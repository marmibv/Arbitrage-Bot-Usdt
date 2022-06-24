from binance import Client
from time import time


def get_pairs():
    return client.get_all_tickers()


# TODO: 1) maybe it should be checking pair for pumps/dumps
#   because there can be a bad order book and the bot will make big loses
def sort_pairs(unsorted_pairs):
    whitelist = []
    n = 1
    for ticker in unsorted_pairs:
        pair, price = ticker["symbol"], ticker["price"]
        if check_trading(pair):
            # if check daily volume, so put condition right here, before getting order book
            # this is because of the high ping

            # this strings are for check_volume_by_order_book
            # it calculates, how much coins we can buy using current deposit (see at the very bottom)
            base, quote = separate_symbols(pair)
            if base is False and quote is False:
                continue
            base_price, quote_price = separate_prices(quote, price)

            order_book = client.get_order_book(symbol=pair)
            if check_volume_by_order_book(base_price, quote_price, order_book):
                whitelist.append(pair)
                print(f"{n}. {pair}")
                n += 1
            else:
                print("\t\t", pair)
    return whitelist


def get_symbol_ticker(base, quote):
    if base == quote == "USDT":
        return {"symbol": "USDTUSDT", "price": 1}
    elif base == quote:
        raise ValueError(f"Base and quote ({base}, {quote}) are the same")
    else:
        return client.get_symbol_ticker(symbol=f"{base}{quote}")


# TODO: bids and asks strings must to be in other place
#   calculate average price is gonna be used in other functions too
def check_volume_by_order_book(base_price, quote_price, order_book):
    # this strings always create lists of 2 tuples of the same length
    # the first one is all prices from order book, the number of which appropriate our precision
    # the second one is all volumes corresponding to the prices
    bids = list(zip(*[list(map(float, bid)) for bid in order_book["bids"][:BID_ASK_OFFSET + 1]]))
    asks = list(zip(*[list(map(float, ask)) for ask in order_book["asks"][:BID_ASK_OFFSET + 1]]))

    # this strings calculate, how much of a current base coin we can buy or sell using our deposit in USDT
    average_asks = calculate_average_price(asks)
    base_can_buy = DEPOSIT / quote_price / average_asks * (1 - COMMISSION_RATE) ** 2
    base_can_sell = DEPOSIT / base_price * calculate_average_price(bids) / average_asks * (1 - COMMISSION_RATE) ** 3
    return sum(bids[1]) >= base_can_sell and sum(asks[1]) >= base_can_buy


# TODO: it's strange, that the function needs already zipped list — write a function for zipping
# for now it needs zipped list (first tuple — prices, second tuple — volumes)
def calculate_average_price(orders):
    all_volume = sum(orders[1])
    average_price = 0
    for i in range(len(orders[0])):
        average_price += orders[0][i] * orders[1][i] / all_volume

    return average_price


# TODO: think about calculating good volumes automatically (if it's really needed for the bot)
#   update all quote volumes
# CONFIGURATION FUNCTION
# NOT USED
def check_volume_daily(pair, volume):
    representative_volumes = {
        "USDT": 5000000,
        "BUSD": 1000000,
        "USDC": 1000000,
        "TUSD": 500000,
        "BTC": 20,
        "ETH": 100,
        "BNB": 200
    }
    # return representative_volumes[pair] <= volume
    pass


def check_trading(pair):
    return client.get_symbol_info(symbol=pair)["status"] == "TRADING"


# TODO: it has to find all possible chains, so
#   1) it has to search more, than 3-pairs chains (maybe add and arg for maximum pairs per chain)
#   2) if (1) is done, so it has to search through unusual chains like ADAUSDT-ADABTC-XRPBTC-BTCUSDT
#   3) maybe update it, so the function searches for not only coin-to-usdt, but also coin-to-btc/eth/other quote
def get_chains(pairs):
    chains = []
    for i in range(len(pairs)):
        pair = pairs[i]
        base, quote = separate_symbols(pair)

        base_to_usdt = f"{base}USDT"
        quote_to_usdt = f"{quote}USDT"
        if base_to_usdt in pairs and quote_to_usdt in pairs:
            chains.extend(((base_to_usdt, pair, quote_to_usdt), (quote_to_usdt, pair, base_to_usdt)))

    return chains


# TODO: rewrite logic to use ALL the existing quotes
#   (note, that some quotes trade not to USDT, but USDT trades to that quotes)
def get_quotes():
    quote_usdt = "USDT BTC BNB BUSD ETH TUSD USDC XRP DOGE PAX USDS TRX EUR BKRW GBP AUD DAI USDP UST DOT".split(" ")
    usdt_quote = "NGN RUB TRY ZAR IDRT UAH BIDR BRL BVND".split(" ")
    exclude = "VAI".split(" ")

    # return {"quote_usdt": quote_usdt, "usdt_quote": usdt_quote, "exclude": exclude}
    return quote_usdt


# TODO: 1) write a function for getting bids and asks from order book
#   (don't forget about precision at the very bottom)
#   3) write a function of calculating swaps through Binance
def find_appropriate_chain(chains):
    if len(chains):
        print(chains, len(chains), end="\n\n")
        while True:
            for i in range(len(chains)):
                chain = chains[i]
                approximate_profit_after_fees = calculate_chain(chain)
                if approximate_profit_after_fees > DEPOSIT:
                    print("\t\t", " ".join(chain))
                    print("\t\t", f"{approximate_profit_after_fees} USDT")
                    print("\t\t", f"Profit: {round((approximate_profit_after_fees / DEPOSIT - 1) * 100, 2)}%")
                    return chain
                print(" ".join(chain))
                print(f"{approximate_profit_after_fees} USDT")
                print(f"Profit: {round((approximate_profit_after_fees / DEPOSIT - 1) * 100, 2)}%")
                print()
            print()
    else:
        print("\nThere's no single chain :(")
        return None


# TODO: 1) rewrite this for more then 3 pairs in chain
def define_strategy(chain):
    strategy = ["BUY"]

    base, quote = separate_symbols(chain[0])
    following = base
    for i in range(1, len(chain)):
        base, quote = separate_symbols(chain[i])
        if base == following:
            following = quote
            strategy.append("SELL")
        else:
            following = base
            strategy.append("BUY")
    return strategy


# TODO: there are quotes, that trade not to USDT, but USDT trades to them. FIX IT!
def separate_symbols(pair):
    for quote in get_quotes():
        if quote == pair[-len(quote):]:
            base = pair[:-len(quote)]
            return base, quote
    return False, False


# TODO: there are quotes, that trade not to USDT, but USDT trades to them. FIX IT!
def separate_prices(quote, price):
    quote_price = float(get_symbol_ticker(quote, "USDT")["price"])
    base_price = float(price) * quote_price
    return base_price, quote_price


def calculate_chain(chain):
    coins = DEPOSIT
    strategy = define_strategy(chain)
    coins_on_stage = []
    for i in range(len(chain)):
        pair = chain[i]
        action = strategy[i]
        orders = client.get_order_book(symbol=pair)

        if action == "BUY":
            orders = list(zip(*[list(map(float, ask)) for ask in orders["asks"][:BID_ASK_OFFSET + 1]]))
            average_price = calculate_average_price(orders)
            coins = coins / average_price
        else:
            orders = list(zip(*[list(map(float, bid)) for bid in orders["bids"][:BID_ASK_OFFSET + 1]]))
            average_price = calculate_average_price(orders)
            coins = coins * average_price

        coins_on_stage.append(coins * (1 - COMMISSION_RATE))
    return coins_on_stage[-1]


# TODO: here is the second time, when define strategy is called, so, maybe I should fix it
def execute_chain(chain):
    coins = DEPOSIT
    strategy = define_strategy(chain)
    for i in range(len(chain)):
        pair = chain[i]
        action = strategy[i]
        if action == "BUY":
            buy_market(pair, coins)
        else:
            sell_market(pair, coins)


# TODO: replace with the real market order (only when everything is done!)
def buy_market(pair, coins):
    client.create_test_order(
        symbol=pair,
        side=Client.SIDE_BUY,
        type=Client.ORDER_TYPE_MARKET,
        quantity=coins
    )
    print("\t\t", f"BUY {coins} {pair}")


# TODO: replace with the real market order (only when everything is done!)
def sell_market(pair, coins):
    client.create_test_order(
        symbol=pair,
        side=Client.SIDE_SELL,
        type=Client.ORDER_TYPE_MARKET,
        quantity=coins
    )
    print("\t\t", f"SELL {coins} {pair}")


# TODO: make a timer that updates every 24h to recalculate whitelist
def main():
    # switch this to True when testing for getting and sorting symbols
    # switch this to False to skip long (on my computer) sorting symbols
    time_is_over = False
    if time_is_over:
        whitelist = sort_pairs(get_pairs()[:10])
        with open("tickers.txt", "w") as file:
            file.write("\n".join([str(pair) for pair in whitelist]))
    else:
        with open("tickers.txt", "r") as file:
            whitelist = file.read().split("\n")

    chains = get_chains(whitelist)

    appropriate_chain = find_appropriate_chain(chains)
    execute_chain(appropriate_chain)


# TODO: 1) make not fixed commission rate
#   because the library has function of getting commission rate for the specific pair
#   2) maybe it should have something like user interface (but should think about it if it's really needed)
#   3) maybe this could have dynamic deposit, because the final result could vary on different values
#   4) maybe this could search through a lot of other exchanges: Binance, Kraken, Bitmex etc
#   5) maybe this could search arbitrage ideas not only on exchanges, but make very complex chains like
#   buy ADAUSDT on Binance, withdraw ADA to crypto wallet (TrustWallet, Argent, Metamask), swap ADA to other coin
#   through other exchange (Kraken, Swap Pancake, UnicornSwap etc) ... then swap to USDT
if __name__ == "__main__":
    api_key = "zPVPyDE5a98fBYeplQb9RlpaK2G6ZSnqhP6Pl3dAFkNvXBPffaBN51KiXs0i7rZy"
    api_secret = "zBx2YGnXYUKGSu19K460Ce3s1sxzNvl0f0q3a0Zzgfs4Wh0LE9p5RXfX6ystuGZt"
    client = Client(api_key, api_secret)

    DEPOSIT = 100
    BID_ASK_OFFSET = 1
    COMMISSION_RATE = 0.000

    main()
