from decouple import config

series_name = config("SERIES_NAME")
print("Hello YouTube")
print(f"Welcome to {series_name}")
