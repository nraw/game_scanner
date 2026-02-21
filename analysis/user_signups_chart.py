import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dotenv import load_dotenv
load_dotenv('.env')
from game_scanner.db import get_collection

coll = get_collection('users')
dates = []
for doc in coll.stream():
    ct = doc.create_time
    dates.append(ct.date())

dates.sort()

unique_dates = sorted(set(dates))
cumulative = []
count = 0
for d in unique_dates:
    count += dates.count(d)
    cumulative.append((d, count))

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

ax1.hist(dates, bins=20, edgecolor='black', alpha=0.7, color='steelblue')
ax1.set_title('User Signups Over Time')
ax1.set_ylabel('New Users')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax1.tick_params(axis='x', rotation=45)

cum_dates, cum_counts = zip(*cumulative)
ax2.plot(cum_dates, cum_counts, marker='.', color='steelblue', linewidth=2)
ax2.fill_between(cum_dates, cum_counts, alpha=0.2, color='steelblue')
ax2.set_title('Cumulative Users')
ax2.set_ylabel('Total Users')
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('user_signups.png', dpi=150)
print('Saved to user_signups.png')
