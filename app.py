#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import git
import os
import datetime
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

st.title('Weekdays of commit and when to expect the next commit')

# to use different styles, make sure to reload the default to always get clean results
# plt.style.available
def use_style(style):
    plt.style.use('default')
    plt.style.use(style)

if not os.path.exists('./covid_19'):
    git_url = 'https://github.com/openZH/covid_19.git'
    repo = git.Repo.clone_from(git_url, 'covid_19')
else:
    repo = git.Repo(os.environ.get('REPO_PATH', 'covid_19'), odbt=git.GitCmdObjectDB)

WEEKS = 3
days = WEEKS * 7
start_date = datetime.datetime.today() - datetime.timedelta(days=days)
start_date

cantons = [
    "AG",
    "AI",
    "AR",
    "BE",
    "BL",
    "BS",
    "FR",
    "GE",
    "GL",
    "GR",
    "JU",
    "LU",
    "NE",
    "NW",
    "OW",
    "SG",
    "SH",
    "SO",
    "SZ",
    "TG",
    "TI",
    "UR",
    "VD",
    "VS",
    "ZG",
    "ZH",
]

selected_canton = st.sidebar.selectbox(
    'Select a canton',
    cantons
)

@st.cache
def load_data(canton, start_date):
    commits = list(repo.iter_commits(paths=f'fallzahlen_kanton_total_csv_v2/COVID19_Fallzahlen_Kanton_{canton}_total.csv', since=start_date.date().isoformat()))

    data = []
    for commit in commits:
        if commit.committer.name == 'GitHub Action Scraper':
            committer = 'Scraper'
        else:
            committer = 'Other'
        date = commit.committed_datetime.replace(tzinfo=None).date()
        data.append({'canton': canton, 'date': date, 'committer': committer})
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df

def add_additional_cols(df):
    df_new = df.groupby(['date', 'committer']).count().reset_index()
    df_new = df_new.rename(columns={"canton": "date_count"})
    df_new['diff'] =  df_new['date']- df_new['date'].shift(1)
    df_new['weekday'] = df_new[['date']].apply(lambda x: datetime.datetime.strftime(x['date'], '%A'), axis=1)

    # drop the first entry
    df_new.drop(df_new.head(1).index, inplace=True)
    
    return df_new

def add_missing_days(df):
    df_new = df.groupby(['weekday']).count()[['date']].reset_index()
    df_new = df_new.rename(columns={"date": "weekday_count"})
    
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_new = df_new.set_index(['weekday']).reindex(weekdays, fill_value=0).reset_index()
    mapping = {day: i for i, day in enumerate(weekdays)}
    key = df_new['weekday'].map(mapping)
    df_new = df_new.iloc[key.argsort()]
    return df_new

data_load_state = st.text('Loading data...')
df_canton = load_data(selected_canton, start_date)
data_load_state.text('Loading data...done!')


use_style('fivethirtyeight')
fig, ax = plt.subplots(figsize=(15, 10), dpi=300)
fig.suptitle(f"Weekday of commits\nover last {WEEKS} weeks for {selected_canton}", fontsize=32, fontweight='bold');

df_canton = add_additional_cols(df_canton)

mean_time_diff = df_canton['diff'].mean()
now =  datetime.datetime.now()
next_commit_date = df_canton[['date']].to_dict('records')[-1]['date'] + mean_time_diff

diff = next_commit_date - now
if diff.total_seconds() < -(60*60*24):
    ax.text(0.05, 1.05, f"The next commit is overdue since {abs(diff.days)} days, was expected on {next_commit_date.date()}", transform=ax.transAxes, bbox=dict(facecolor='red', alpha=0.5), fontsize=32)
else:
    ax.text(0.05, 1.05, f"Next commit expected on {next_commit_date.date()} (in {diff.days + 1} days)", transform=ax.transAxes, bbox=dict(facecolor='blue', alpha=0.5), fontsize=32)
    
# commits by scraper
df_canton_scraper = df_canton[df_canton.committer == 'Scraper'].reset_index(drop=True)
df_canton_scraper = add_additional_cols(df_canton_scraper)
df_canton_scraper = add_missing_days(df_canton_scraper)

# commits by others
df_canton_other = df_canton[df_canton.committer == 'Other'].reset_index(drop=True)
df_canton_other = add_additional_cols(df_canton_other)
df_canton_other = add_missing_days(df_canton_other)

# weekdays
df_canton_weekday = pd.merge(df_canton_scraper, df_canton_other, on='weekday', suffixes=('_scraper', '_other'))

ax.set_ylabel('Number of commits')
ax.set_xlabel('Weekday')
ax.yaxis.set_major_locator(MaxNLocator(integer=True))

df_canton_weekday.plot(kind='bar', x='weekday', y=['weekday_count_scraper', 'weekday_count_other'], stacked=True, ax=ax, label=('Scraper', 'Others'))

# Matplotlib idiom to reverse legend entries 
handles, labels = ax.get_legend_handles_labels()
ax.legend(reversed(handles), reversed(labels))

ax.xaxis.label.set_visible(False)
plt.setp(ax.get_xticklabels(), rotation=0, ha='center')

plt.tight_layout(rect=[0.05, 0.05, 1, 0.97])
fig.subplots_adjust(hspace=0.8, top=0.8)
st.pyplot(fig)

st.text(f"Commit data of {selected_canton}:")
st.dataframe(df_canton)
