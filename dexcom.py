from decouple import config
from pydexcom import Dexcom
from twilio.rest import Client
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    'dexcom.log', maxBytes=1000000, backupCount=3)
handler.setFormatter(formatter)
logger.addHandler(handler)


def should_send_message(dex):
    if dex.value <= 80:
        return True
    if dex.value <= 100 and dex.trend_description == "falling":
        return True
    if dex.trend_description == "falling quickly":
        return True
    if dex.trend_description == "rising quickly":
        return True

    return False


def build_message_body(dex):
    return (
        f"Blood sugar update:\n"
        f"Current reading is {dex.value}\n"
        f"Trend is {dex.trend_description} ({dex.trend_arrow})\n"
        f"Reading taken at {dex.time}"
    )


def main():
    try:
        dexcom = Dexcom(
            config("DEXCOM_USERNAME"),
            config("DEXCOM_PASSWORD")
        )
        bg = dexcom.get_current_glucose_reading()

        if should_send_message(bg):
            result = build_message_body(bg)
            print(result)

            client = Client(config("TWILIO_ACCOUNT"), config("TWILIO_TOKEN"))

            message = client.messages.create(
                to=config("TWILIO_TO_NUMBER"),
                from_=config("TWILIO_FROM_NUMBER"),
                body=result
            )
            logger.info("Sending message, result:", message)
        else:
            result = build_message_body(bg)
            logger.info("Did not meet condition to send, exiting successfully")
    except BaseException as err:
        logger.error(f"Unexpected {err=}, {type(err)=}")
        raise


if __name__ == "__main__":
    main()
