import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from environs import Env

env = Env()
env.read_env()

DATABASE_DSN = env('DATABASE_DSN')
db_config = DATABASE_DSN.split()
db_details = {param.split('=')[0]: param.split('=')[1] for param in db_config}
db_connection_str = f"postgresql://{db_details['user']}:{db_details['password']}@{db_details['host']}/{db_details['dbname']}"
engine = create_engine(db_connection_str)

def load_data(engine):
    # Запрос SQL для извлечения данных
    query = """
    SELECT encrypted_user_id, title, date, location, department, description, amount
    FROM complaints
    """
    
    # Загрузка данных в DataFrame
    df = pd.read_sql(query, engine)
    return df

# Загрузка данных
data = load_data(engine)

# Базовая настройка страницы
st.title("Дашборд жалоб на коррупцию")
st.sidebar.header("Фильтры")

# Виджеты для фильтрации данных
locations = st.sidebar.multiselect("Выберите локацию:", options=data['location'].unique())
departments = st.sidebar.multiselect("Выберите орган власти:", options=data['department'].unique())

# Применение фильтров
if locations:
    data = data[data['location'].isin(locations)]
if departments:
    data = data[data['department'].isin(departments)]

data['date'] = pd.to_datetime(data['date'])

# Извлечение часа и дня недели
data['hour'] = data['date'].dt.hour
data['weekday'] = data['date'].dt.weekday

# Преобразование дней недели из чисел в названия
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
data['weekday_name'] = data['weekday'].apply(lambda x: days[x])

# График количества жалоб по датам
fig_date = px.histogram(data, x='date', title='Количество жалоб по датам', labels={'date': 'Дата'})
st.plotly_chart(fig_date)

# Распределение жалоб по часам
fig_hour = px.histogram(data, x='hour', title='Распределение жалоб по часам', labels={'hour': 'Час'})
st.plotly_chart(fig_hour)

# Распределение жалоб по дням недели
fig_weekday = px.histogram(data, x='weekday', title='Распределение жалоб по дням недели', labels={'weekday': 'День недели'}, category_orders={'weekday': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']})
st.plotly_chart(fig_weekday)

# Распределение жалоб по местоположению
fig_location = px.histogram(data, x='location', title='Распределение жалоб по местоположению', labels={'location': 'Локация'})
st.plotly_chart(fig_location)

# Распределение жалоб по органам власти
fig_department = px.histogram(data, x='department', title='Распределение жалоб по органам власти', labels={'department': 'Орган власти'})
st.plotly_chart(fig_department)

# Распределение сумм взяток
fig_amount = px.histogram(data, x='amount', title='Распределение сумм взяток', labels={'amount': 'Сумма взятки'})
st.plotly_chart(fig_amount)