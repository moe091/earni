import schema as sc
import edgar2 as ed
import database as db

schema = sc.financial_metrics




def update_ticker(ticker):
    print("Scraping data for " + ticker)
    edgar = ed.EdgarInstance(ticker)
    data = edgar.populate_schema(schema)

    for k, v in data.items():
        print(f"\n\nUpdating {ticker} - {k}:")
        for prop, val in v.items():
            print(f"{prop}: {val}")

        db.update_financial_data(ticker, k, v)



if __name__ == "__main__":
    with open("./tickerlist.txt", "r") as file:
        lines = file.readlines()

    while len(lines) > 5380:
        ticker = lines.pop(0).strip()
        update_ticker(ticker)
        with open("./tickerlist.txt", "w") as file:
            for l in lines:
                file.write(l)

