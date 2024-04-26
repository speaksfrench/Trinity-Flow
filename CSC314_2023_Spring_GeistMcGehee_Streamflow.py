import hydrofunctions as hf, matplotlib.pyplot as plt, matplotlib.dates as mdates, numpy as np, statistics
import matplotlib
import humanize # makes stuff easier for humans to read
matplotlib.use('TkAgg') # specify we need a GUI
from datetime import datetime, timedelta
import argparse

# NOTE: accounting for leap years gives me a dilemma -- either I start later or end later, but either way it looks weird. That or I ommit a day, which I don't want to.

def main(args):
    plt.figure(figsize=(12, 7))
    trinity_burnt_ranch_id = '11527000'
    anchor = datetime.strptime(str(args.anchor), '%Y-%m-%d')
    data = list()
    amount_of_years = 10
    column = 'USGS:11527000:00060:00000'

    # Get information from NWIS for every year in the last ten years
    # Download data

    def is_leap_year(year):
        if year % 4 == 0:
            if year % 100 == 0:
                if not year % 400 == 0:
                    return False
            return True
        return False


    count_leaps = 0 # count leap years
    for year in range(amount_of_years):
        #leap = False
        #if is_leap_year(year): leap = True
        #if leap and before_leap: count_leaps += 1 # if the current date is before leap day, we want to subtract an extra day from this year too, otherwise not
        
        if year > 0: 
            begin_date = (anchor - timedelta(days=(365 * year) + 14 + count_leaps)).isoformat()       # `year` years in the past, accounting for the amount of leap years
            end_date = (anchor - timedelta(days=(365 * year)) + timedelta(days=7)).isoformat()    # ending date is year years in the past and seven days into the future
        else: 
            begin_date = (anchor - timedelta(days=14)).isoformat()
            end_date = anchor.isoformat()                                                        # if year = 0, then it is the anchor year and we cannot go 7 days in the future
        print(begin_date)

        year_raw = hf.NWIS(trinity_burnt_ranch_id, 'iv', start_date=begin_date, end_date=end_date, verbose=False)
        data.append(year_raw)
        #if leap: count_leaps += 1 # if the end_date is after leap day, we don't want this year to account for its own leap day, so we only increment count_leaps for the next year
        #haiiii :3 - michael

    # Creates a list of dataframes of every NWIS data entry
    dframes = list()
    for i in data:
        dframes.append(i.df('discharge')[:])

    # Calculate the average flows for each year
    sum_flows = list()
    for i in dframes: # iterates through every dataframe 
        sum = 0
        for ii in i[column]:
            sum += ii * 15 * 60
        sum_flows.append(sum)

    # Find the max and min flow years
    max_year_idx = sum_flows.index(max(sum_flows[1:])) # [1:] is to avoid the first year, not necessary in this case but avoids possible bugs
    min_year_idx = sum_flows.index(min(sum_flows[1:]))

    # The "derivative"
    curr_flow1 = dframes[0][column].iloc[-1]
    curr_flow2 = dframes[0][column].iloc[-2]
    derivative = (curr_flow1 - curr_flow2) * 4

    # Get the mean and stdev for every year
    entries = [[] for i in range(len(dframes[1][column]))]

    for year in dframes[1:]: # skip the current year
        for idx, entry in enumerate(year[column]): # appends every time frame to the appropriate time frame section
            entries[idx].append(entry)

    means = list()
    stds = list()
    for time in entries:
        if np.isnan(time).any(): # makes sure there are no NaN values 
            temp = list()
            for i in time: # in the case of a NaN value, just create a new array without the NaN and move on.
                if not np.isnan(i):
                    temp.append(i)
            stds.append(statistics.stdev(temp))
            means.append(statistics.mean(temp))
            continue
        stds.append(statistics.stdev(time))
        means.append(statistics.mean(time))

    # df format:
    #                            USGS:11527000:00060:00000
    #datetimeUTC
    #2021-03-26 04:15:00+00:00                     1030.0
    #2021-03-26 04:30:00+00:00                     1030.0

    # Formats the dates
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())

    max_x_axis = [datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in dframes[max_year_idx].index] # makes a list of every time in the max year and removes the year
    min_x_axis = [datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in dframes[min_year_idx].index]



    # get x ticks based off month and year only
    x_ticks = list()
    for idx, i in enumerate(max_x_axis):
        if idx % 500 == 0:
            x_ticks.append(datetime.strptime(str(i)[5:10], "%m-%d"))

    plt.xticks(x_ticks) 

    curr_year = dframes[0]
    max_year = dframes[max_year_idx]
    min_year = dframes[min_year_idx]

    # Create a range of dates
    x_axis = np.arange(anchor - timedelta(days = 21), anchor, timedelta(days=1)).astype(datetime)
    #plt.xticks(min(x_axis), max(x_axis))

    # Current
    # TODO: current year starts not exactly at the right time

    curr_date_ym = datetime.strptime(str(dframes[0].index[-1])[5:19],"%m-%d %H:%M:%S")

    # For some odd reason, the current year starts a litte bit earlier  than the other years. I really don't know why this is.
    plt.plot([datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in dframes[0].index], curr_year, 'k', label=f'Current year ({anchor.isoformat()[0:4]})')

    # Max
    plt.plot(max_x_axis, max_year, 'g', label=f'Max year ({(anchor - timedelta(days = max_year_idx * 365)).isoformat()[0:4]})')

    # Minimum
    plt.plot(min_x_axis, min_year, 'b', label=f'Min year ({(anchor - timedelta(days = min_year_idx * 365)).isoformat()[0:4]})')

    # STDev top
    # Y-vals
    std_top_yvals = list()
    std_bottom_yvals = list()

    for idx, i in enumerate(means):
        std_top_yvals.append(means[idx] + 0.5 * stds[idx])
        std_bottom_yvals.append(means[idx] - 0.5 * stds[idx])

    plt.plot(max_x_axis, std_top_yvals, color='0.5', linestyle='--')
    plt.plot(max_x_axis, std_bottom_yvals, color='0.5', linestyle='--')
    plt.gca().fill_between(max_x_axis, std_top_yvals, std_bottom_yvals, color='0.9')

    # Linear Regression 
    current_year = dframes[0]
    x_vals = [idx for idx, i in enumerate(current_year.index)] # to_numeric does not make them reasonable indices, but in fact large integers
    y_vals = list(dframes[0][column])

    x_bar = statistics.mean(x_vals)
    y_bar = statistics.mean(y_vals)
    x_std = statistics.stdev(x_vals)
    y_std = statistics.stdev(y_vals)

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


    plt.axvline(x = curr_date_ym, color = 'r', linestyle = '--', label='{0}'.format(str(anchor)[5:16])) # converts the current date to m/y and plots a line on that date (marks the beginning of the regression)
    plt.plot(regression_xvals, regression_yvals, color = 'k')

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
    parser.add_argument('anchor', metavar='anchor', type=str, help='Usage: <time> (YYYY-MM-DD)', default=str(datetime.now().isoformat()))  
    args = parser.parse_args()
    main(args)