import json
import requests
from dash import Dash, html, Input, Output, State, dcc
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from config import API_KEY
from datetime import datetime, timedelta

# Инициализация приложения с темой COSMO
app = Dash(__name__, external_stylesheets=[dbc.themes.COSMO])

# Функция для получения ключа локации
def get_location_key(location):
    location_url = 'http://dataservice.accuweather.com/locations/v1/cities/autocomplete'
    params = {
        'apikey': API_KEY,
        'q': location,
        'language': 'ru-ru'
    }
    try:
        location_response = requests.get(location_url, params=params)
        location_response.raise_for_status()
        location_data = location_response.json()
        if location_data:
            return location_data[0]['Key']
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f'Ошибка при запросе локации: {e}')
        return None

# Функция для получения координат по ключу локации
def get_location_coords(location_key):
    coords_url = f'http://dataservice.accuweather.com/locations/v1/{location_key}'
    params = {
        'apikey': API_KEY,
        'language': 'ru-ru'
    }
    try:
        coords_response = requests.get(coords_url, params=params)
        coords_response.raise_for_status()
        coords_data = coords_response.json()
        if coords_data:
            latitude = coords_data['GeoPosition']['Latitude']
            longitude = coords_data['GeoPosition']['Longitude']
            return latitude, longitude
        else:
            return None, None
    except requests.exceptions.RequestException as e:
        print(f'Ошибка при запросе координат: {e}')
        return None, None

# Функция для получения прогноза погоды
def get_weather(location_key):
    weather_url = f'http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}'
    params = {
        'apikey': API_KEY,
        'language': 'ru-ru',
        'details': 'true',
        'metric': 'true'
    }
    try:
        weather_response = requests.get(weather_url, params=params)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        if weather_data:
            return weather_data['DailyForecasts']
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f'Ошибка при запросе погоды: {e}')
        return None

# Функция для обработки данных о погоде
def get_weather_info(weather_json, days, time_of_day_ru):
    time_of_day = 'Day' if time_of_day_ru == 'День' else 'Night'

    if weather_json:
        weather_data = []
        for day in range(days):
            temp = weather_json[day][time_of_day]['WetBulbGlobeTemperature']['Average']['Value']
            humid = weather_json[day][time_of_day]['RelativeHumidity']['Average']
            wind_speed = weather_json[day][time_of_day]['Wind']['Speed']['Value']
            prec_prob = weather_json[day][time_of_day]['PrecipitationProbability']
            description = weather_json[day][time_of_day]['LongPhrase']

            weather_data.append({
                'Дата': datetime.now() + timedelta(days=day),
                'Температура (°C)': temp,
                'Влажность (%)': humid,
                'Скорость ветра (м/с)': wind_speed,
                'Вероятность осадков (%)': prec_prob,
                'Описание': description
            })

        return pd.DataFrame(weather_data)
    else:
        return pd.DataFrame()

# Разметка веб-интерфейса
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Прогноз погоды", style={"textAlign": "center"}), className="mb-4")
    ]),

    dbc.Row([
        dbc.Col([
            html.Label("Начало маршрута:"),
            dcc.Input(id="start-location-input", type="text", placeholder="Москва", style={"marginRight": "10px"}),
        ], width=4),
        dbc.Col([
            html.Label("Конец маршрута:"),
            dcc.Input(id="end-location-input", type="text", placeholder="Санкт-Петербург", style={"marginRight": "10px"}),
        ], width=4),
        dbc.Col([
            html.Label("Промежуточные точки:"),
            dcc.Input(id="intermediate-location-input", type="text", placeholder="Омск", style={"marginRight": "10px"}),
            html.Button("Добавить точку", id="add-intermediate-button", n_clicks=0, className="mt-2"),
        ], width=4),
    ]),

    dbc.Row([
        dbc.Col(html.Div(id="locations-list", style={"marginTop": "20px"}), width=12)
    ]),

    dbc.Row([
        dbc.Col([
            html.Label("Выберите количество дней для прогноза:"),
            dcc.Slider(
                id="days-slider",
                min=1,
                max=5,
                step=1,
                value=3,  # Значение по умолчанию
                marks={i: str(i) for i in range(1, 6)},
            ),
        ], width=6),
        dbc.Col([
            html.Label("Выберите время суток:"),
            dcc.Dropdown(
                id="time-of-day-dropdown",
                options=[
                    {"label": "День", "value": "День"},
                    {"label": "Ночь", "value": "Ночь"},
                ],
                value="День",  # Значение по умолчанию
            ),
        ], width=6),
    ]),

    dbc.Row([
        dbc.Col([
            html.Label("Выберите параметр для графика:"),
            dcc.RadioItems(
                id="parameter-radio",
                options=[
                    {"label": "Температура", "value": "Температура (°C)"},
                    {"label": "Влажность", "value": "Влажность (%)"},
                    {"label": "Скорость ветра", "value": "Скорость ветра (м/с)"},
                    {"label": "Вероятность осадков", "value": "Вероятность осадков (%)"},
                ],
                value="Температура (°C)",  # Значение по умолчанию
                labelStyle={"display": "block"},
            ),
        ], width=6),
        dbc.Col([
            html.Button("Обновить данные", id="refresh-button", n_clicks=0, style={"marginTop": "20px"}),
        ], width=6),
    ]),

    dbc.Row([
        dbc.Col([
            dcc.Graph(id="weather-graph"),
        ], width=6),
        dbc.Col([
            dcc.Graph(id="weather-map"),
        ], width=6),
    ]),
])

# Хранение точек маршрута
locations = []

# Обновление списка точек маршрута
@app.callback(
    Output("locations-list", "children"),
    Output("intermediate-location-input", "value"),  # Очистка поля ввода
    [Input("add-intermediate-button", "n_clicks")],
    [State("start-location-input", "value"),
     State("end-location-input", "value"),
     State("intermediate-location-input", "value")],
)
def update_locations_list(n_clicks, start_location, end_location, intermediate_location):
    if n_clicks > 0 and intermediate_location:
        locations.append(intermediate_location)
        return html.Ul([html.Li(loc) for loc in [start_location, *locations, end_location] if loc]), ""  # Очистка поля ввода
    return html.Ul([html.Li(loc) for loc in [start_location, *locations, end_location] if loc]), intermediate_location

# Обновление графика и карты
@app.callback(
    [Output("weather-graph", "figure"),
     Output("weather-map", "figure")],
    [Input("parameter-radio", "value"),
     Input("days-slider", "value"),
     Input("time-of-day-dropdown", "value"),  # Исправлено на правильный идентификатор
     Input("refresh-button", "n_clicks")],
    [State("start-location-input", "value"),
     State("end-location-input", "value"),
     State("intermediate-location-input", "value")],
)
def update_graph_and_map(parameter, days, time_of_day, n_clicks, start_location, end_location, intermediate_location):
    # Обновление данных при нажатии на кнопку "Обновить данные"
    if n_clicks > 0:
        all_data = pd.DataFrame()
        unique_locations = set()

        for loc in [start_location, *locations, end_location]:
            if loc and loc not in unique_locations:
                unique_locations.add(loc)
                location_key = get_location_key(loc)
                latitude, longitude = get_location_coords(location_key)
                weather_json = get_weather(location_key)
                df = get_weather_info(weather_json, days, time_of_day)
                if not df.empty:
                    df["Место"] = loc
                    df["Latitude"] = latitude
                    df["Longitude"] = longitude
                    all_data = pd.concat([all_data, df])


        if "Дата" not in all_data.columns:
            return go.Figure(), go.Figure()

        # График
        fig_graph = px.line(
            all_data,
            x="Дата",
            y=parameter,
            color="Место",
            title=f"Прогноз погоды: {parameter} ({time_of_day})",
            markers=True,
        )
        fig_graph.update_layout(
            xaxis_title="Дата",
            yaxis_title=parameter,
            template="plotly_white",
        )

        # Карта
        fig_map = go.Figure()
        for _, row in all_data.iterrows():
            if row["Место"] not in unique_locations:
                continue
            fig_map.add_trace(go.Scattermapbox(
                lat=[row["Latitude"]],
                lon=[row["Longitude"]],
                mode="markers+text",
                text=row["Место"],
                marker=dict(size=10, color="red"),
                hovertemplate=(
                    f"<b>{row['Место']}</b><br>"
                    f"Дата: {row['Дата'].strftime('%Y-%m-%d')}<br>"
                    f"Температура: {row['Температура (°C)']}°C<br>"
                    f"Влажность: {row['Влажность (%)']}%<br>"
                    f"Скорость ветра: {row['Скорость ветра (м/с)']} м/с<br>"
                    f"Вероятность осадков: {row['Вероятность осадков (%)']}%<br>"
                    f"Координаты: ({row['Latitude']}, {row['Longitude']})"
                )
            ))
            unique_locations.remove(row["Место"])

        # Линия маршрута
        if len(all_data) > 1:
            fig_map.add_trace(go.Scattermapbox(
                lat=all_data["Latitude"],
                lon=all_data["Longitude"],
                mode="lines",
                line=dict(width=2, color="blue"),
                hoverinfo="none"
            ))

        fig_map.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=55.7558, lon=37.6173),  # Центрирование на Москве
                zoom=5,
            ),
            margin=dict(l=0, r=0, t=0, b=0),
        )

        return fig_graph, fig_map

    return go.Figure(), go.Figure()


if __name__ == "__main__":
    app.run_server(debug=True)