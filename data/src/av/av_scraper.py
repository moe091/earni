import av
import time


if __name__ == "__main__":
    with open("./ftickers.txt", "r") as file:
        lines = file.readlines()
        lines = [l.strip() for l in lines]

    while len(lines) > 0:
        ticker = lines.pop(0)
        try:
            print(f"Processing {ticker}...")
            av.populate_ticker(ticker)
            print(f"Processed {ticker}")

            #update tickerlist incase script crashes, it will pick off exactly where it left off automatically
            with open("./tickerlist.txt", "w") as file:
                for l in lines:
                    file.write(l + "\n")
        except Exception as e:
            print(f"Failed to process {ticker}: {str(e)}")
            with open("./failed_tickers.txt", "a") as file:
                file.write(f"{ticker}\n{str(e)}\n\n")


        time.sleep(0.7) # Sleep for half a second to avoid rate limiting
