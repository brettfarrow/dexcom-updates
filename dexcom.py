from decouple import config
from pydexcom import Dexcom
from twilio.rest import Client
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

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


def should_send_message(dex, time):
    time_result, data_result = False, False

    try:
        if (time - dex.time).total_seconds() < 60:
            time_result = True

        if dex.value <= 80:
            data_result = True
        if dex.value <= 100 and dex.trend_description == "falling":
            data_result = True
        if dex.trend_description == "falling quickly":
            data_result = True
        if dex.trend_description == "rising quickly":
            data_result = True
    except:
        if dex == None and time.minute % 15 == 0:
            return True

    return time_result and data_result


def should_make_call(dex, time):
    time_result, data_result = True, False

    if (time - dex.time).total_seconds() < 60:
        time_result = True
    if dex.value <= 55 or dex.value >= 300:
        data_result = True

    return time_result and data_result


def build_message_body(dex):
    reading_time = dex.time.strftime("%I:%M %p on %B %d")
    return (
        f"Blood sugar update:\n"
        f"Current reading is {dex.value}\n"
        f"Trend is {dex.trend_description} ({dex.trend_arrow})\n"
        f"Reading taken at {reading_time}"
    )


def main():
    try:
        start_time = datetime.now()
        dexcom = Dexcom(
            config("DEXCOM_USERNAME"),
            config("DEXCOM_PASSWORD")
        )
        bg = dexcom.get_current_glucose_reading()

        if should_send_message(bg, start_time):
            result = build_message_body(bg)
            print(result)

            client = Client(config("TWILIO_ACCOUNT"), config("TWILIO_TOKEN"))

            message = client.messages.create(
                to=config("TWILIO_TO_NUMBER"),
                from_=config("TWILIO_FROM_NUMBER"),
                body=result
            )
            # Use result for just the SMS, message for Twilio API response
            logger.info(f"Sending message, result: {message}")
        else:
            logger.info("Did not meet condition to send, exiting successfully")

        if should_make_call(bg, start_time):
            try:
                client
            except NameError:
                client = Client(config("TWILIO_ACCOUNT"),
                                config("TWILIO_TOKEN"))

            client.calls.create(
                url=config("TWIML_LOCATION_URL"),
                to=config("TWILIO_TO_NUMBER"),
                from_=config("TWILIO_FROM_NUMBER"),
            )
        else:
            logger.info("Did not meet condition to call, exiting successfully")
    except BaseException as err:
        logger.error(f"Unexpected {err=}, {type(err)=}")
        raise


if __name__ == "__main__":
    main()
