import logging
import azure.functions as func
import requests
import json
from azure.eventhub import EventHubProducerClient, EventData
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from datetime import datetime

app = func.FunctionApp()

@app.timer_trigger(schedule="*/60 * * * * *", arg_name="myTimer", run_on_startup=True,
            use_monitor=False) 
def weatherapifunction(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')

    #REPLACE EVENT_HUB_NAME and EVENT_HUB_NAMESPACE! This is how it looked for me.
    #
    #
    EVENT_HUB_NAME = "weatherstreameventhub"
    EVENT_HUB_NAMESPACE = "weatherstreamingnamespace311.servicebus.windows.net"
    #
    #
    credential = DefaultAzureCredential()

    producer = EventHubProducerClient(
        fully_qualified_namespace=EVENT_HUB_NAMESPACE,
        eventhub_name=EVENT_HUB_NAME,
        credential=credential
    )

    def send_event(event):
        event_data_batch = producer.create_batch()
        event_data_batch.add(EventData(json.dumps(event)))
        producer.send_batch(event_data_batch)

    def handle_response(response):
        if response.status_code == 200:
            return response.json()
        else:
            return f"Error {response.status_code}, {response.text}"

    def get_current(base_url, api_key, location):
        params = {'key': api_key, 'q': location, 'aqi': 'yes'}
        return handle_response(requests.get(f"{base_url}/current.json", params=params))

    def get_forecast(base_url, api_key, location, days):
        params = {'key': api_key, 'q': location, 'days': days}
        return handle_response(requests.get(f"{base_url}/forecast.json", params=params))

    def get_alerts(base_url, api_key, location):
        params = {'key': api_key, 'q': location, 'alerts': 'yes'}
        return handle_response(requests.get(f"{base_url}/alerts.json", params=params))

    def flattened_data(current_weather, forecast_weather, alerts):
        def safe_datetime(value, fmt="%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                return None

        def safe_float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def safe_int(value):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return None

        def combine_date_and_time(date_str, time_str, date_fmt="%Y-%m-%d", time_fmt="%I:%M %p"):
            try:
                return datetime.strptime(f"{date_str} {time_str}", f"{date_fmt} {time_fmt}").strftime("%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                return None

        location_data = current_weather.get("location", {})
        current = current_weather.get("current", {})
        condition = current.get("condition", {})
        air_quality = current.get("air_quality", {})
        forecast = forecast_weather.get("forecast", {}).get("forecastday", [])
        alert_list = alerts.get("alerts", {}).get("alert", [])

        alert = alert_list[0] if alert_list else {}

        today_date = location_data.get('localtime', '')[:10]
        first_day = forecast[0] if forecast else {}
        sunrise_today_val = first_day.get('astro', {}).get('sunrise')
        sunset_today_val = first_day.get('astro', {}).get('sunset')

        flattened_list = []

        for day in forecast:
            date_val = day.get('date')
            sunrise_val = day.get('astro', {}).get('sunrise')
            sunset_val = day.get('astro', {}).get('sunset')

            logging.info(f"[Forecast] Combining sunrise: date='{date_val}' with time='{sunrise_val}'")
            logging.info(f"[Forecast] Combining sunset: date='{date_val}' with time='{sunset_val}'")

            flattened_list.append({
                'name': location_data.get('name'),
                'region': location_data.get('region'),
                'country': location_data.get('country'),
                'lat': location_data.get('lat'),
                'lon': location_data.get('lon'),
                'localtime': safe_datetime(location_data.get('localtime')),
                'forecast_date': date_val,
                'forecast_key': f"{location_data.get('localtime')} | {date_val}",
                'maxtemp_c': safe_float(day.get('day', {}).get('maxtemp_c')),
                'mintemp_c': safe_float(day.get('day', {}).get('mintemp_c')),
                'avgtemp_c': safe_float(day.get('day', {}).get('avgtemp_c')),
                'condition': day.get('day', {}).get('condition', {}).get('text'),
                'sunrise': combine_date_and_time(date_val, sunrise_val),
                'sunset': combine_date_and_time(date_val, sunset_val),
                'sunrise_today': combine_date_and_time(today_date, sunrise_today_val),
                'sunset_today': combine_date_and_time(today_date, sunset_today_val),
                'temp_c': safe_float(current.get('temp_c')),
                'is_day': safe_int(current.get('is_day')),
                'condition_text': condition.get('text'),
                'condition_icon': condition.get('icon'),
                'wind_kph': safe_float(current.get('wind_kph')),
                'wind_degree': safe_int(current.get('wind_degree')),
                'wind_dir': current.get('wind_dir'),
                'pressure_in': safe_float(current.get('pressure_in')),
                'precip_in': safe_float(current.get('precip_in')),
                'humidity': safe_int(current.get('humidity')),
                'cloud': safe_int(current.get('cloud')),
                'feelslike_c': safe_float(current.get('feelslike_c')),
                'uv': safe_float(current.get('uv')),
                'air_quality_co': safe_float(air_quality.get('co')),
                'air_quality_no2': safe_float(air_quality.get('no2')),
                'air_quality_o3': safe_float(air_quality.get('o3')),
                'air_quality_so2': safe_float(air_quality.get('so2')),
                'air_quality_pm2_5': safe_float(air_quality.get('pm2_5')),
                'air_quality_pm10': safe_float(air_quality.get('pm10')),
                'air_quality_us_epa_index': safe_int(air_quality.get('us-epa-index')),
                'air_quality_gb_defra_index': safe_int(air_quality.get('gb-defra-index')),
                'alert_headline': alert.get('headline'),
                'alert_severity': alert.get('severity'),
                'alert_description': alert.get('desc'),
                'alert_instruction': alert.get('instruction')
            })

        return flattened_list

    def get_secret_from_keyvault(vault_url, secret_name):
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=vault_url, credential=credential)
        return secret_client.get_secret(secret_name).value

    def fetch_weather_data():
        try:
            base_url = "http://api.weatherapi.com/v1/"
            location = "Tucson"
            
            # REPLACE THIS VAULT_URL and API_KEY_SECRET_NAME with yours!
            #
            #
            VAULT_URL = "https://kv-weather-streaming-311.vault.azure.net/"
            API_KEY_SECRET_NAME = "weatherapikey"
            #
            #
            weatherapikey = get_secret_from_keyvault(VAULT_URL, API_KEY_SECRET_NAME)

            current_weather = get_current(base_url, weatherapikey, location)
            forecast_weather = get_forecast(base_url, weatherapikey, location, 3)
            alerts = get_alerts(base_url, weatherapikey, location)

            forecast_entries = flattened_data(current_weather, forecast_weather, alerts)
            for entry in forecast_entries:
                print(json.dumps(entry, indent=2))
                send_event(entry)

        except Exception as e:
            logging.error("🔥 ERROR in fetch_weather_data: %s", str(e), exc_info=True)

    fetch_weather_data()
