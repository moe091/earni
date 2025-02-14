# EARNI

## Web Application for Visualizing Stock Price Movement Relative to Earnings Report Data

Earni will be divided into a couple of subprojects:
    1. An API written in Python that can analyze financial data based on various parameters and create various visualizations
        - This project also entails retrieving data(using the SEC's EDGAR API and Yahoo Finance API), Storing it efficiently in a database(Probable PostgreSQL, still need to research options though), as well as some scripts and tools for administrating and maintaining everything
    2. A web application that allows users to search and analyze financial data as well as create custom visualizations
        - Users can choose a stock or subset of stocks(either a list of tickers, or a sector, or a whole exchange) and a time range, to choose which stocks to analyze and what date ranges to look at stock prices and earnings reports for. All analysis will be centered around earnings reports, so they will essentially be choosing which earnings reports to look at by company and date range. Stock price is only gathered for the days after each earning report, and is used to compare price changes directly after an earnings report relative to the data points in the actual earnings report.
        - Users can further filter OUT earnings reports based on criteria related to the reports themself. For example: "Select only earnings reports where EPS was at least 5% more than the expected EPS" or "Select only earnings reports where revenue increased relative to the previous earnings report", etc. Users can apply and combine as many filters as they want. There will also be filters based on the stock price or the company itself, such as "Only search companies with a market cap of 10 billion or more" or "Only search companies with a share price above $5". Ideally, I'd like to implement stock price filters that are relative to earnings dates, e.g. "Only select earnings reports in which the companies stock price decreased by 5% or more in the week leading up to the earnings report" since this kind of info should be very relevant to how the price moves AFTER the earnings report as well(e.g. filtering by companies that decreased a lot just before earnings, but then heavily beat expectations, would be interesting).
        - !!!! BONUS !!!! Allow users to create Alerts based on their filters. If the data analysis and visualization works out well, and users are able to identify useful trends - meaning they identify a set of filters that identifies a large number earnings reports where, for almost every one of them, the companies stock price increased by a large amount in the week following the report - then they can create an alert that will notify them when any company on their list files an earnings report that meets those same criteria. The EDGAR database is updated very quickly(usually within minutes of an earnings report) so it should be possible to scan all newly posted earnings reports regularly and compare them against filters/alerts setup by users.

    



## Project Notes and Todos (for personal use):

#### Random:
look into harpoon
vim

### Todo:
Finished gather basic financial and stock price data. Going to move on to creating the visualization and filter/query functions and the api endpoint to request them. 
I will probably add a lot more financial data(revenue and costs and whatnot, maybe even some sentiment analysis on articles or ER calls) later but for now it's better to 
get a minimum-viable-product up and running. Once I work through all of the other stuff I'll have a MUCH better idea of what info I want to get and how best to store and manage it.

To start out I'll just add a couple simple visualizations with a few basic filtering options:
    - select all stocks or a user-submitted list of stocks
    - filter based on date range(of earnings reports), eps values(reported, estimated, diff), and x_day stock price difference(e.g. price_change > 20% at 5-day mark)
        - LATER: add filters based on pre-earnigns price change. e.g. select only reports where minus_1_day is 10% less than minus_10_day, AND eps_reported - eps_estimate is > 0.08.
    - generate bar graph. 
        - y-axis can be eps values or x_day price diffs.
        - x-axis can also be eps vals or price diffs(e.g. grouped by eps or price diff 0-0.1, 0.1-0.2, 0.2-0.3, etc), or a subset of the stocks. Or it can just be 'days'(will show (avg)price diff at each x-day mark. 1,2,3,4,5,10, etc)
        - for some types of bar graphs, we can have double or triple bars. e.g. showing avg, top 25%, and bottom 25%. Or maybe open + close price. 
        - LATER: custom x-axis can be created. User clicks 'add bar', and then can create sub-filters that allow them to select a subset of the reports and then name that subset and assign it to a bar. e.g. someone may create custom
            sub-filters for (close_minus_1 / close_minus_5) = < 0.8, 0.8 - 0.9, 0.9-1, 1-1.1, 1.1-1.2, and > 1.2. This can allow them to see important differences, e.g.:
            y-axis is price change on day after earnigns. x-axis is divided into the sub-filters mentioned above. The user could discover that "stocks that were down a lot in the week prior to earnings had a MUCH higher bounceback after a positive ER"





### scratch pad

SELECT ph.ticker, ph.report_date, er.eps_estimate, er.eps_reported, (er.eps_estimate / er.eps_reported), er.surprise, ph.close_minus_1, ph.close_plus_1, (ph.close_plus_1 - ph.close_minus_1) FROM price_history ph JOIN earnings_reports er ON ph.ticker = er.ticker AND ph.report_date = er.date WHERE (er.eps_estimate / er.eps_reported) > 1.20;


find all reports where close_plus_1 is 20% greater than close_minus_1.

select ph.ticker, ph.report_date, ph.close_minus_1, ph.close_plus_1, (ph.close_plus_1::double precision / ph.close_minus_1) as price_change, er.eps_estimate, er.eps_reported, (er.eps_reported - er.eps_estimate) as eps_diff FROM price_history ph JOIN earnings_reports er ON ph.ticker = er.ticker AND ph.report_date = er.date WHERE (ph.close_plus_1::double precision / ph.close_minus_1) > 1.2;