from decouple import config
from pydexcom import Dexcom
from twilio.rest import Client

dexcom = Dexcom(
    config("DEXCOM_USERNAME"),
    config("DEXCOM_PASSWORD")
)
bg = dexcom.get_current_glucose_reading()

if bg.value <= 80:
    result = f"blood sugar is {bg.value}, trend is {bg.trend_description} ({bg.trend_arrow}) at {bg.time}"

    client = Client(config("TWILIO_ACCOUNT"), config("TWILIO_TOKEN"))

    message = client.messages.create(
        to=config("TWILIO_TO_NUMBER"),
        from_=config("TWILIO_FROM_NUMBER"),
        body=result
    )
else:
    print("All is clear for now")
