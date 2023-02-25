from decouple import config
from pydexcom import Dexcom
from twilio.rest import Client
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import pytz

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


class FakeDexcom(object):
    pass


def write_timestamp(dex):
    # Convert the time to an ISO-8601 timestamp
    timestamp = dex.time.isoformat()

    # Write the timestamp to a file called "timestamp.txt"
    with open("timestamp.txt", "w") as f:
        f.write(timestamp)


def read_timestamp():
    # Read the timestamp from the file and return it as a time object
    try:
        with open('timestamp.txt', 'r') as f:
            data = f.read()
            return datetime.fromisoformat(data)
    except:
        FIRST_TIMESTAMP = '1970-01-01T00:00:00'
        placeholder = FakeDexcom()
        placeholder.time = datetime.fromisoformat(FIRST_TIMESTAMP)
        write_timestamp(placeholder)
        return FIRST_TIMESTAMP


def should_send_message(dex):
    time_result, data_result = False, False
    last_reading = read_timestamp()

    if last_reading != dex.time:
        time_result = True

    if dex.value <= 80:
        data_result = True
    if dex.value <= 100 and dex.trend_description == "falling":
        data_result = True
    if dex.value >= 300:
        data_result = True
    if dex.trend_description == "falling quickly":
        data_result = True
    if dex.trend_description == "rising quickly":
        data_result = True

    logger.info(f"should_send_message time_result: {time_result}")
    logger.info(f"should_send_message data_result: {data_result}")

    return time_result and data_result


def should_make_call(dex):
    time_result, data_result = False, False
    last_reading = read_timestamp()

    # Call every reading for an urgent low, every 15 minutes for a high
    try:
        if last_reading != dex.time:
            time_result = True
            if dex.value <= 55 or dex.value >= 300:
                data_result = True
                if dex.value >= 300 and datetime.now().minute % 15 != 0:
                    time_result = False
    except:
        return False

    logger.info(f"should_make_call time_result: {time_result}")
    logger.info(f"should_make_call data_result: {data_result}")

    return time_result and data_result


def build_message_body(dex):
    reading_time = dex.time.astimezone(pytz.timezone(
        config('LOCAL_TIMEZONE'))).strftime("%I:%M %p on %B %d")
    return (
        f"Blood sugar update:\n"
        f"Current reading is {dex.value}\n"
        f"Trend is {dex.trend_description} ({dex.trend_arrow})\n"
        f"Reading taken at {reading_time}"
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
            # Use result for just the SMS, message for Twilio API response
            logger.info(f"Sending message, result: {message}")
        else:
            logger.info("Did not meet condition to send, exiting successfully")

        if should_make_call(bg):
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
        write_timestamp(bg)
    except BaseException as err:
        logger.error(f"Unexpected {err=}, {type(err)=}")
        raise


if __name__ == "__main__":
    main()
