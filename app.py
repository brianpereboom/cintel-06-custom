# Imports
  # requests (for alphavantage API)

# Reactive Aspects 
  # Use history() to get current stock data
  # history() will be called when inputs change

# UI Page Inputs
  # Choose stock ticker
  # Choose indicators and time frames

# UI Sidebar Components
  # express.ui.input_text()
  # express.ui.input_checkbox_group()

# UI Main Content
  # express.ui.card()
  # Line plot or candlestick chart for stock history

import requests
import pandas as pd
from shiny.express import input, ui
from shinywidgets import render_altair
from shiny import reactive, render
import altair as alt

@reactive.calc()
def get_stock_data():
    APIKEY = "demo" #"BSY3N7ZO1IH3X10V"

    r = {}
    if input.period() == "Daily":
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={input.symbol.get()}&apikey={APIKEY}'
        r = requests.get(url).json()[f'Time Series (Daily)']
    elif input.period() == "Weekly":
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={input.symbol.get()}&apikey={APIKEY}'
        r = requests.get(url).json()[f'Weekly Time Series']
    elif input.period() == "Monthly":
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol={input.symbol.get()}&apikey={APIKEY}'
        r = requests.get(url).json()[f'Monthly Time Series']
    elif "min" in input.period():
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={input.symbol.get()}&interval={input.period()}&apikey={APIKEY}'
        r = requests.get(url).json()[f'Time Series ({input.period()})']
    
    data = pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])
    for key, value in r.items():
        data.loc[len(data)] = {"datetime": key, "open": value["1. open"], "high": value["2. high"], "low": value["3. low"], "close": value["4. close"], "volume": value["5. volume"]}

    data['datetime'] = data['datetime'].apply(pd.to_datetime)
    data.sort_values(by='datetime', inplace=True, ascending=True)
    
    for column in data.columns:
        if column != "datetime":
            data[column] = data[column].apply(pd.to_numeric)
    
    PH9 = [max(data['close'][i:i + 9]) for i in range(len(data) - 9)]
    PL9 = [min(data['close'][i:i + 9]) for i in range(len(data) - 9)]
    PH26 = [max(data['close'][i:i + 26]) for i in range(len(data) - 26)]
    PL26 = [min(data['close'][i:i + 26]) for i in range(len(data) - 26)]
    PH52 = [max(data['close'][i:i + 52]) for i in range(len(data) - 52)]
    PL52 = [min(data['close'][i:i + 52]) for i in range(len(data) -52)]
    CL = [(h + l) / 2 for h, l in zip(PH9, PL9)]
    BL = [(h + l) / 2 for h, l in zip(PH26, PL26)]
    data["Leading Span A (senkou span A)"] = ([None] * 52) + [(c + b) / 2 for c, b in zip(CL[17:-26], BL[:-26])]
    data["Leading Span B (senkou span B)"] = ([None] * 78) + [(h + l) / 2 for h, l in zip(PH52[:-26], PL52[:-26])]
    data["Lagging Span (chikou span)"] = list(data["close"][26:]) + ([None] * 26)
    data["Color"] = ['green' if a > b else 'red' for a, b in zip(data["Leading Span A (senkou span A)"], data["Leading Span B (senkou span B)"])]
    return data

with ui.sidebar():
    ui.input_text('symbol', "Symbol", value="IBM")
    ui.input_selectize("period", "Period", choices=[
        "1min", "5min",
        #"15min", "30min", "60min",
        "Daily", "Weekly", "Monthly"
    ], selected="Daily")
    ui.input_checkbox_group("ichimoku", "Ichimoku Cloud", choices=["Senkou", "Chikou"])

with ui.layout_columns():
    @render.data_frame
    def display_df():
        return render.DataGrid(get_stock_data(), width="100%")

height, width = 'container', 'container'

with ui.card():
    @render_altair
    def stock_chart():
        data = get_stock_data()

        # https://altair-viz.github.io/gallery/candlestick_chart.html
        open_close_color = alt.condition(
            "datum.open <= datum.close",
            alt.value("#06982d"),
            alt.value("#ae1325")
        )
        base = alt.Chart(data).encode(
            alt.X('datetime:T')
                .title("Date/Time")
                .axis(format='%m/%d %H:%m', labelAngle=-45),
            color=open_close_color
        ).properties(
            height=height,
            width=width
        )
        rule = base.mark_rule().encode(
            alt.Y('low:Q')
                .title('Price')
                .scale(zero=False),
            alt.Y2('high:Q')
        )
        bar = base.mark_bar().encode(
            alt.Y('open:Q'),
            alt.Y2('close:Q')
        )
        
        volume_chart = alt.Chart(data).mark_bar().encode(
            alt.X(
                "datetime:T"
            ),
            alt.Y(
                "volume:Q"
            ).title("Volume"),
            alt.ColorValue("blue"),
            opacity=alt.value(0.1)
        ).properties(
            height=height,
            width=width
        )
        
        charts = rule + bar
        
        if "Senkou" in input.ichimoku():
            charts += alt.Chart(data).mark_line().encode(
                alt.X(
                    "datetime:T"
                )
                .title("Date/Time")
                .axis(format='%m/%d %H:%m', labelAngle=-45),
                alt.Y(
                    "Leading Span A (senkou span A):Q"
                ),
                alt.ColorValue("green")
            ).properties(
                height=height,
                width=width
            ) + alt.Chart(data).mark_line().encode(
                alt.X(
                    "datetime:T"
                )
                .title("Date/Time")
                .axis(format='%m/%d %H:%m', labelAngle=-45),
                alt.Y(
                    "Leading Span B (senkou span B):Q"
                ),
                alt.ColorValue("red")
            ).properties(
                height=height,
                width=width
            ) + alt.Chart(data).mark_area().encode(
                x='datetime:T',
                y="Leading Span A (senkou span A):Q",
                y2="Leading Span B (senkou span B):Q",
                color=alt.Color('Color:N', scale=alt.Scale(domain=['red','green'], range=['#FF8888','#88FF88']))
            )
        if "Chikou" in input.ichimoku():
            color_map = {"green": "#00FF00", "red": "#FF0000"}
            charts += alt.Chart(data).mark_line().encode(
                alt.X(
                    "datetime:T"
                )
                .title("Date/Time")
                .axis(format='%m/%d %H:%m', labelAngle=-45),
                alt.Y(
                    "Lagging Span (chikou span):Q"
                )
            ).properties(
                height=height,
                width=width
            )
        return (
            alt.layer(
                charts.interactive(),
                volume_chart
            ).resolve_scale(y='independent')
        )
