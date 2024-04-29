import hydrofunctions as hf, matplotlib.pyplot as plt, matplotlib.dates as mdates, numpy as np, statistics
import matplotlib
import humanize # makes stuff easier for humans to read
matplotlib.use('TkAgg') # specify GUI
from datetime import datetime, timedelta
import argparse

# TODO:
# 2023-09-27 has the same min/max line (?)
# If leap year is in date range, code runs but end date is off by one

def main(args):
    plt.figure(figsize=(12, 7))
    trinity_burnt_ranch_id = '11527000'
    anchor = datetime.strptime(str(args.anchor), '%Y-%m-%d')
    data = []
    amount_of_years = 10
    column = 'USGS:11527000:00060:00000'
    leap_day = datetime(2000, 2, 29)

    # Get information from NWIS for every year in the last ten years
    # Download data
    for year in range(amount_of_years):
        curr_year = anchor.year - year
        begin_date = datetime(curr_year, anchor.month, anchor.day) - timedelta(days=14)
        if year > 0: 
            end_date = (datetime(curr_year, anchor.month, anchor.day) + timedelta(days=7))    # ending date is year years in the past and seven days into the future
            if end_date.month == leap_day.month and end_date.day == leap_day.day: # Prevents data from ending on leap day
                end_date += timedelta(days=1) 
        else: 
            end_date = anchor                                                        # if year = 0, then it is the anchor year and we cannot go 7 days in the future

        print('Fetching date range:', begin_date, 'to', end_date)

        year_raw = hf.NWIS(trinity_burnt_ranch_id, 'iv', start_date=begin_date.isoformat(), end_date=end_date.isoformat(), verbose=False)
        data.append(year_raw)

    # Creates a list of dataframes of every NWIS data entry
    dframes = []
    for i in data:
        dframes.append(i.df('discharge')[:])

    cleaned_dfs = [] # Remove leap day from every dataframe
    for dframe in dframes:
        to_cut = []
        for index in dframe.index:
            if str(index)[5:10] == '02-29': # Datetime doesn't recognize timestamp leap year days as valid, so skip them
                to_cut.append(index)
        cleaned_dframe = dframe.drop(to_cut)
        cleaned_dfs.append(cleaned_dframe)
    dframes = cleaned_dfs

    # Calculate the average flows for each year
    sum_flows = []
    for i in dframes: # iterates through every dataframe 
        sum = 0
        for ii in i[column]:
            sum += ii * 15 * 60
        sum_flows.append(sum)

    # Find the max and min flow years
    max_year_idx = sum_flows.index(max(sum_flows[1:])) # avoid the first year
    min_year_idx = sum_flows.index(min(sum_flows[1:]))

    # The "derivative"
    curr_flow1 = dframes[0][column].iloc[-1]
    curr_flow2 = dframes[0][column].iloc[-2]
    derivative = (curr_flow1 - curr_flow2) * 4

    # Get the mean and stdev for every year
    entries = []
    for year in dframes[1:]: # skip the current year
        for idx, entry in enumerate(year[column]): # appends every time frame to the appropriate time frame section
            try:
                entries[idx].append(entry)
            except IndexError: # if for some reason this array is too short, append another
                entries.append([])
                entries[idx].append(entry)

    means = []
    stds = []
    for time in entries:
        if np.isnan(time).any(): # makes sure there are no NaN values 
            temp = []
            for i in time: # in the case of a NaN value, just create a new array without the NaN and move on.
                if not np.isnan(i):
                    temp.append(i)
            stds.append(statistics.stdev(temp))
            means.append(statistics.mean(temp))
            continue
        stds.append(statistics.stdev(time))
        means.append(statistics.mean(time))

    # Formats the dates
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())


    max_x_axis = [datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in dframes[max_year_idx].index] # Used to be code to account for Leap Years, but they have been removed
    min_x_axis = [datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in dframes[min_year_idx].index]
            
    # get x ticks based off month and year only
    x_ticks = []
    for idx, i in enumerate(max_x_axis):
        if idx % 500 == 0:
            x_ticks.append(datetime.strptime(str(i)[5:10], "%m-%d"))
    plt.xticks(x_ticks) 

    # Get the dataframe for each year
    curr_year = dframes[0]
    max_year = dframes[max_year_idx]
    min_year = dframes[min_year_idx]

    # Current
    curr_date_ym = datetime.strptime(str(dframes[0].index[-1])[5:19],"%m-%d %H:%M:%S") # current year and month based on anchor

    # For some odd reason, the current year starts a litte bit earlier  than the other years. I really don't know why this is.
    plt.plot([datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in dframes[0].index], curr_year, 'k', label=f'Anchor year ({anchor.isoformat()[0:4]})')

    # Max
    max_year_date = (anchor - timedelta(days = max_year_idx * 365)).isoformat()[0:4]
    plt.plot(max_x_axis, max_year, 'g', label=f'Max year ({max_year_date})')

    # Minimum
    min_year_date = (anchor - timedelta(days = min_year_idx * 365)).isoformat()[0:4]
    plt.plot(min_x_axis, min_year, 'b', label=f'Min year ({min_year_date})')

    # STDev top
    # Y-vals
    std_top_yvals = []
    std_bottom_yvals = []

    for idx, i in enumerate(means):
        std_top_yvals.append(means[idx] + 0.5 * stds[idx])
        std_bottom_yvals.append(means[idx] - 0.5 * stds[idx])

    # TODO: Make plot start on anchor day and not after 
    # Average fill
    plt.plot(min_x_axis, std_top_yvals, color='0.5', linestyle='--')
    plt.plot(min_x_axis, std_bottom_yvals, color='0.5', linestyle='--')
    plt.gca().fill_between(min_x_axis, std_top_yvals, std_bottom_yvals, color='0.9')

    # Mean graph
    plt.plot(min_x_axis, means, color='w', linestyle='dashdot', label='Mean')


    # Linear Regression 
    current_year = dframes[0]
    x_vals = [idx for idx, i in enumerate(current_year.index)]

    # If a NaN value is found, replaces entry with last valid data. 
    # The logic behind this is that two points are probably not that far off from each other, so a missing point is probably similar to the last entry.
    y_vals = [it if not np.isnan(it) else dframes[0][column].iloc[idx - 1] for idx, it in enumerate(dframes[0][column])] 

    x_bar = statistics.mean(x_vals)
    y_bar = statistics.mean(y_vals)
    x_std = statistics.stdev(x_vals)
    
    # TODO: Fix: for some dates, NWIS has NaN values. If I just remove those from the data, my axis will be off.
    try:
        y_std = statistics.stdev(y_vals)
    except AttributeError: 
        print('NWIS\'s database is missing entries for that timeframe. Try another anchor date.')
        quit()

    total = 0.0
    for i in range(len(x_vals)): # yes, I did not use dataframes for this. it seemed easier without them, as using dataframes also returns a dataframe for r, which seems impractical and confusing
        total += (x_vals[i] - x_bar) * (y_vals[i] - y_bar)

    r = total / ((len(x_vals) - 1) * x_std * y_std)
    slope = r * (y_std / x_std)

    regression_end_date = anchor + timedelta(days=7)

    # 1) creates an arange of values starting from the current date and going 7 days into the future then 2) removes the year from all of those values
    increment = 1 / 24 / 60 * 15 # 15-minute increment
    x_start = dframes[0][column].iloc[-1] # the final value of the current year (the y-intercept of the regression line)
    regression_xvals = [datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in np.arange(anchor + timedelta(days=0.25), regression_end_date, timedelta(days=increment)).astype(datetime)] # oddly enough, we have to start the regression line 0.25 days after the current date
    regression_yvals = [i * slope + x_start for i in range(len(regression_xvals))]

    plt.axvline(x = curr_date_ym, color = 'r', linestyle = '--', label='{0}'.format(str(anchor)[5:10])) # converts the current date to m/y and plots a line on that date (marks the beginning of the regression)
    plt.plot(regression_xvals, regression_yvals, color = 'k')

    # Plot titling
    plt.legend(loc="upper left")
    plt.suptitle('Trinity River at Hoopa (CFS)', fontsize=20)

    current_flow = humanize.intcomma(sum_flows[0] / 43560)[:10]
    change = str(derivative)[:4].strip('-').strip('.')
    if derivative > 0: plt.title(f'{current_flow} acre-feet : increasing {change} CFS/hr') # if derivative is positive, say increasing, decreasing, or stagnant
    elif derivative < 0: plt.title(f'{current_flow} acre-feet : dropping {change} CFS/hr')
    else: plt.title(f'{current_flow} acre-feet : no change ({change} CFS/hr)')
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Graphs the maximum, minimum, current, and average flow of the Trinity River over the past 10 years.')
    parser.add_argument('anchor', metavar='anchor', type=str, help='Usage: main.py <time> (YYYY-MM-DD)', default=str(datetime.now().isoformat()))  
    try:
        args = parser.parse_args()
    except:
        print('Usage: main.py <time> (YYYY-MM-DD)')
        quit()
    main(args)