from pybit import usdt_perpetual
from pybit.exceptions import FailedRequestError
from selenium import webdriver
import time as tempo
from selenium.webdriver.common.by import By
from pyvirtualdisplay.xvfb import XvfbDisplay
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from requests.exceptions import RequestException, ConnectionError
import subprocess
from pyvirtualdisplay.abstractdisplay import XStartTimeoutError
import os
import signal

# we will need the number of decimal of a number


def nb_decimales(x):
    # Convertir x en chaîne de caractères
    x_str = str(x)
    # Trouver la position du point décimal
    if x == int(x):
        return 0
    else:
        index_decimal = x_str.index('.')

        # Calculer la longueur de la chaîne de caractères après le point décimal
        nb_decimales = len(x_str[index_decimal+1:])

        return nb_decimales

# we will need to acess a file with our api keys


def apikey():
    f = open("cleapi.txt", "r")
    keys = [f.readline()[:-1], f.readline()]
    f.close()
    return keys

# Before opening a position, we need to size our position (size vers dollars)


def get_size(currency='BTC', paie=20):
    session_unauth = usdt_perpetual.HTTP(
        endpoint="https://api-testnet.bybit.com"
    )

    # je récupère le prix de la paire à trader
    info_paire = session_unauth.query_mark_price_kline(
        symbol=currency+'USDT',
        interval="D",
        from_time=round(tempo.time())-86400
    )
    prix = info_paire['result'][0]['close']

    # je récupère quel est la quantité minimal tradable
    symbols = (session_unauth.query_symbol())
    for symbole in symbols['result']:
        if symbole['name'] == currency+'USDT':
            min_trading_qty = symbole['lot_size_filter']['min_trading_qty']

            # je calcul quel quantité en coin que représente le prix que je veux payer en euro
            cost_voulu = paie/prix
            cost_ajusté = round(min_trading_qty*(round(cost_voulu *
                                (min_trading_qty**(-1)))), nb_decimales(min_trading_qty))
            if cost_ajusté == 0:
                return min_trading_qty
            return cost_ajusté

# dollar vers size


def get_quantity(currency='BTC', size=0.01):
    session_unauth = usdt_perpetual.HTTP(
        endpoint="https://api-testnet.bybit.com"
    )
    # je récupère le prix de la paire à trader
    info_paire = session_unauth.query_mark_price_kline(
        symbol=currency+'USDT',
        interval="D",
        from_time=round(tempo.time())-86400
    )
    prix = info_paire['result'][0]['close']

    # je calcul que représente la quantité de token en dollars
    cost_voulu = size*prix
    cost_ajusté = round(cost_voulu)
    return cost_ajusté

# First, this code need to open a position on Bybit using API


def open_position(currency='BTC', side='Sell', paie=20):
    keys = apikey()
    session_auth = usdt_perpetual.HTTP(
        endpoint="https://api.bybit.com",
        api_key=keys[0],
        api_secret=keys[1],
    )

    # J'ouvre une position sur l'exchange bybit
    position = session_auth.place_active_order(
        symbol=currency+'USDT',
        side=side,
        order_type="Market",
        qty=get_size(currency, paie),
        time_in_force="GoodTillCancel",
        reduce_only=False,
        close_on_trigger=False,
        position_idx=0
    )
    print(position['result']['side'] + ' ' + str(position['result']['qty']) + ' ' +
          position['result']['symbol'] + ' at price ' + str(position['result']['price']))
    return (position['result']['qty'])


# Then we need to grab some info from the Bybit API


def get_paires_valables():
    session_unauth = usdt_perpetual.HTTP(
        endpoint="https://api-testnet.bybit.com"
    )

    # je récupère quel est la quantité minimal tradable
    dic_symbols = session_unauth.query_symbol()
    symbols = []
    for symbol in dic_symbols['result']:
        if symbol['name'][-4:] == 'USDT' and not (symbol['name'][:3] == 'QNT'):
            symbols += [symbol['name']]
    return symbols

# Then from the binance leaderboard


def get_trade(list_trader, currency_valables_bybit):
    """
    # Set the options for the Edge browser
    edge_options = webdriver.EdgeOptions()

    # on ne veut pas que trop de données soient en cache

    edge_options.add_argument("--disk-cache-size=0")
    edge_options.add_argument("--media-cache-size=0")
    edge_options.add_argument("--disable-cache")
    edge_options.add_argument("--disable-application-cache")

    # Initialize the Edge driver with the options
    driver = webdriver.Edge(options=edge_options)
    """
    driver = webdriver.Edge()
    # On ouvre la page du trader que l'on veut copier
    for trader in list_trader:

        driver.execute_script(
            f"window.open('{trader[1]}', 'new window')")

    # temps d'attente pour permettre le chargement des pages
    tempo.sleep(2)
    list_trades = []
    for index_trader in range(len(list_trader)):
        # revenir au premier onglet
        driver.switch_to.window(driver.window_handles[index_trader])

        # On récupère le tableau avec les trades
        table = driver.find_element(By.XPATH,
                                    "/html/body/div[1]/div[2]/div[1]/div/div[2]/div/div[2]/div/div[2]/div/div/div/div/table")

        # On met chaque ligne dans un tableau
        rows = table.find_elements(By.TAG_NAME, "tr")

        # On compte le nombre de ligne

        num_rows = len(rows)
        first_row = driver.find_element(By.XPATH,
                                        "/html/body/div[1]/div[2]/div[1]/div/div[2]/div/div[2]/div/div[2]/div/div/div/div/table/tbody/tr[2]")

        first_row_count = first_row.find_elements(By.TAG_NAME, "td")
        number_column = len(first_row_count)
        # on va créer une boucle pour récupérer toutes les paires des trades et leurs sens associés
        if number_column < 2:
            list_trades += [None]
        else:
            liste_paire = []
            for indice_paire in range(2, num_rows):
                liste_paire += [[driver.find_element(By.XPATH,
                                                     "/html/body/div[1]/div[2]/div[1]/div/div[2]/div/div[2]/div/div[2]/div/div/div/div/table/tbody/tr["+str(indice_paire)+"]/td[1]/div/div[1]").text, driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[1]/div/div[2]/div/div[2]/div/div[2]/div/div/div/div/table/tbody/tr['+str(indice_paire)+']/td[1]/div/div[2]/div[1]').text, float(driver.find_element(By.XPATH,
                                                                                                                                                                                                                                                                                                                                                                                                                      "/html/body/div[1]/div[2]/div[1]/div/div[2]/div/div[2]/div/div[2]/div/div/div/div/table/tbody/tr["+str(indice_paire)+"]/td[2]").text), 0]]
            # On va ajuster notre liste de paire pour ne garder que ce qui nous intéresse
            for paire in liste_paire:
                for currency in currency_valables_bybit:
                    if paire[0][:-10] == currency:
                        paire[0] = paire[0][:-14]
            indice_memoire = 0
            while indice_memoire != len(liste_paire):
                if len(liste_paire[indice_memoire][0]) > 8:
                    liste_paire.pop(indice_memoire)
                    indice_memoire -= 1
                indice_memoire += 1

        # je récupère la proportion en dollar que représente une position par rapport à toutes les positions ouvertes

            total = 0
            for trade in liste_paire:
                trade[3] = get_quantity(trade[0], trade[2])
                total += trade[3]
            for trade in liste_paire:
                trade[3] = trade[3]/total
            list_trades += [liste_paire]
    driver.quit()
    return list_trades


# dernière MAJ 09/01/2023
# currency_valable_bybit = ['10000NFTUSDT', '1000BONKUSDT', '1000BTTUSDT', '1000LUNCUSDT', '1000XECUSDT', '1INCHUSDT', 'AAVEUSDT', 'ACHUSDT', 'ADAUSDT', 'AGLDUSDT', 'AKROUSDT', 'ALGOUSDT', 'ALICEUSDT', 'ALPHAUSDT', 'ANKRUSDT', 'ANTUSDT', 'APEUSDT', 'API3USDT', 'APTUSDT', 'ARPAUSDT', 'ARUSDT', 'ASTRUSDT', 'AUDIOUSDT', 'AVAXUSDT', 'AXSUSDT', 'BAKEUSDT', 'BALUSDT', 'BANDUSDT', 'BATUSDT', 'BCHUSDT', 'BELUSDT', 'BICOUSDT', 'BITUSDT', 'BLZUSDT', 'BNBUSDT', 'BNXUSDT', 'BOBAUSDT', 'BSVUSDT', 'BSWUSDT', 'BTCUSDT', 'C98USDT', 'CEEKUSDT', 'CELOUSDT', 'CELRUSDT', 'CELUSDT', 'CHRUSDT', 'CHZUSDT', 'CKBUSDT', 'COMPUSDT', 'COTIUSDT', 'CREAMUSDT', 'CROUSDT', 'CRVUSDT', 'CTCUSDT', 'CTKUSDT', 'CTSIUSDT', 'CVCUSDT', 'CVXUSDT', 'DARUSDT', 'DASHUSDT', 'DENTUSDT', 'DGBUSDT', 'DODOUSDT', 'DOGEUSDT', 'DOTUSDT', 'DUSKUSDT', 'DYDXUSDT', 'EGLDUSDT', 'ENJUSDT', 'ENSUSDT', 'EOSUSDT', 'ETCUSDT', 'ETHUSDT', 'ETHWUSDT', 'FILUSDT', 'FITFIUSDT', 'FLMUSDT', 'FLOWUSDT', 'FTMUSDT', 'FXSUSDT', 'GALAUSDT', 'GALUSDT', 'GLMRUSDT', 'GMTUSDT', 'GMXUSDT', 'GRTUSDT', 'GTCUSDT', 'HBARUSDT', 'HNTUSDT', 'HOTUSDT',
#                           'ICPUSDT', 'ICXUSDT', 'ILVUSDT', 'IMXUSDT', 'INJUSDT', 'IOSTUSDT', 'IOTAUSDT', 'IOTXUSDT', 'JASMYUSDT', 'JSTUSDT', 'KAVAUSDT', 'KDAUSDT', 'KLAYUSDT', 'KNCUSDT', 'KSMUSDT', 'LDOUSDT', 'LINAUSDT', 'LINKUSDT', 'LITUSDT', 'LOOKSUSDT', 'LPTUSDT', 'LRCUSDT', 'LTCUSDT', 'LUNA2USDT', 'MAGICUSDT', 'MANAUSDT', 'MASKUSDT', 'MATICUSDT', 'MINAUSDT', 'MKRUSDT', 'MTLUSDT', 'NEARUSDT', 'NEOUSDT', 'OCEANUSDT', 'OGNUSDT', 'OMGUSDT', 'ONEUSDT', 'ONTUSDT', 'OPUSDT', 'PAXGUSDT', 'PEOPLEUSDT', 'QNTUSDT', 'QTUMUSDT', 'REEFUSDT', 'RENUSDT', 'REQUSDT', 'RNDRUSDT', 'ROSEUSDT', 'RSRUSDT', 'RSS3USDT', 'RUNEUSDT', 'RVNUSDT', 'SANDUSDT', 'SCRTUSDT', 'SCUSDT', 'SFPUSDT', 'SHIB1000USDT', 'SKLUSDT', 'SLPUSDT', 'SNXUSDT', 'SOLUSDT', 'STGUSDT', 'STMXUSDT', 'STORJUSDT', 'STXUSDT', 'SUNUSDT', 'SUSHIUSDT', 'SWEATUSDT', 'SXPUSDT', 'THETAUSDT', 'TLMUSDT', 'TOMOUSDT', 'TRBUSDT', 'TRXUSDT', 'TWTUSDT', 'UNFIUSDT', 'UNIUSDT', 'USDCUSDT', 'VETUSDT', 'WAVESUSDT', 'WOOUSDT', 'XEMUSDT', 'XLMUSDT', 'XMRUSDT', 'XNOUSDT', 'XRPUSDT', 'XTZUSDT', 'YFIUSDT', 'YGGUSDT', 'ZECUSDT', 'ZENUSDT', 'ZILUSDT', 'ZRXUSDT']


if __name__ == '__main__':
    on = True
    # we run our browser in a virtual display

    disp = XvfbDisplay()
    disp.start()
    pointer_id = disp._subproc.pid

    # display is active
    nb_traders = int(input('nombre de trader voulu :\n'))

    # je créer une liste qui va contenir les informations de base sur les traders

    list_traders = []
    for i in range(nb_traders):
        trader_name = str(input('nom du trader :\n'))
        trader = str(
            input(f'put the link of {trader_name} page from Binance :\n'))
        paie = int(
            input(f'{trader_name} : Montant en dollars que vous êtes prêt à payer par positions :\n'))
        list_traders += [[trader_name, trader, paie]]

    # INITIALISATION

    currency_valables = get_paires_valables()
    list_trades = []

    # j'ouvre mes positions en fonction de leur proportion chez le trader et je stock les informations du trade dans une liste
    time1 = tempo.time()
    liste_trades_get = get_trade(list_traders, currency_valables)
    print(f'temps pour récupérer les pages web : {tempo.time()-time1}')
    for index_trades in range(len(liste_trades_get)):
        time1 = tempo.time()
        if liste_trades_get[index_trades] != None:
            quantity_used = len(
                liste_trades_get[index_trades])*list_traders[index_trades][2]
            for trade in liste_trades_get[index_trades]:
                if trade[1] == 'Long':
                    print(f'{trader[0]} : INITIALISATION')
                    qty = open_position(
                        trade[0], 'Buy', trade[3]*quantity_used)
                    trade += [trade[3]*quantity_used, qty]
                elif trade[1] == 'Short':
                    print(f'{trader[0]} : INITIALISATION')
                    qty = open_position(
                        trade[0], 'Sell', trade[3]*quantity_used)
                    trade += [trade[3]*quantity_used, qty]
        print(
            f"temps d'initialisation pour {list_traders[index_trades][0]} : {tempo.time()-time1} secondes")
        list_trades += [liste_trades_get[index_trades]]

    os.kill(pointer_id, signal.SIGKILL)
    #display is not active

    # FONCTIONNEMENT

    liste_trade_update = None
    compteur_passage = 0
    time1 = tempo.time()
    while on == True:
        # we run our browser in a virtual display

        disp = XvfbDisplay()
        disp.start()
        pointer_id = disp._subproc.pid

        # display is active

        compteur_passage += 1
        if compteur_passage == round(60/nb_traders):
            compteur_passage = 1
            currency_valables = get_paires_valables()
            print(
                f'temps moyen pour traiter un trader : {(tempo.time()-time1)/60} secondes')
            time1 = tempo.time()
            for index in range(len(list_traders)):
                if list_trades[index] != None:
                    for trade in list_trades[index]:
                        print(
                            f'{list_traders[index][0]} : {trade[1]} {trade[5]} {trade[0]}')
            # je vérifie si le repertoire est bien propre
            result = subprocess.run(
                ["du", "-hs", "/tmp"], capture_output=True, text=True)

            # Print the output
            print(result.stdout)
        # je parcours la list des traders
        liste_trade_update = []
        for trades in list_trades:
            liste_trade_update.append(trades)
        try:
            liste_trade_update = get_trade(list_traders, currency_valables)
        except TimeoutException:
            print('Une erreur de type TimeoutException est survenue'+tempo.ctime())
            # je vérifie si le repertoire est bien propre
            result = subprocess.run(
                ["du", "-hs", "/tmp"], capture_output=True, text=True)

            # Print the output
            print(result.stdout)

        except NoSuchElementException:
            print('une erreur de type NoSuchElement est survenue'+tempo.ctime())
            # je vérifie si le repertoire est bien propre
            result = subprocess.run(
                ["du", "-hs", "/tmp"], capture_output=True, text=True)

            # Print the output
            print(result.stdout)

        except WebDriverException:
            print('Une erreur de type WebDriverException est survenue'+tempo.ctime())

            # je vérifie si le repertoire est bien propre
            result = subprocess.run(
                ["du", "-hs", "/tmp"], capture_output=True, text=True)

            # Print the output
            print(result.stdout)
            if compteur_passage % 5 == 0:
                open_position('BIT', 'Buy', 0.01)

        except RequestException:
            print('Une erreur de type RequestException est survenue'+tempo.ctime())

            # je vérifie si le repertoire est bien propre
            result = subprocess.run(
                ["du", "-hs", "/tmp"], capture_output=True, text=True)

            # Print the output
            print(result.stdout)

        except ConnectionError:
            print('Une erreur de type ConnectionError est survenue'+tempo.ctime())

            # je vérifie si le repertoire est bien propre
            result = subprocess.run(
                ["du", "-hs", "/tmp"], capture_output=True, text=True)

            # Print the output
            print(result.stdout)

        except FailedRequestError:
            print('Une erreur de type FailedRequestError est survenue'+tempo.ctime())

            # je vérifie si le repertoire est bien propre
            result = subprocess.run(
                ["du", "-hs", "/tmp"], capture_output=True, text=True)

            # Print the output
            print(result.stdout)
            tempo.sleep(1801)
        except XStartTimeoutError:
            print('Une erreur de type XStartTimeoutError est survenue'+tempo.ctime())

            # je vérifie si le repertoire est bien propre
            result = subprocess.run(
                ["du", "-hs", "/tmp"], capture_output=True, text=True)

            # Print the output
            print(result.stdout)
        for index in range(len(list_traders)):

            indexes_to_pop = []
            indexes_to_add = []

            if liste_trade_update[index] == None and list_trades[index] == None:
                pass
            elif liste_trade_update[index] == list_trades[index]:
                pass
            elif liste_trade_update[index] == None:
                print('fermeture des trades du trader '+list_traders[index][0])
                for trade in list_trades[index]:
                    if trade[1] == 'Long':
                        if trade[5] < 0:
                            qty = open_position(trade[0], 'Buy', get_quantity(
                                trade[0], abs(trade[5])))
                        else:
                            qty = open_position(
                                trade[0], 'Sell', get_quantity(trade[0], trade[5]))
                    elif trade[1] == 'Short':
                        if trade[5] < 0:
                            qty = open_position(trade[0], 'Sell', get_quantity(
                                trade[0], abs(trade[5])))
                        else:
                            qty = open_position(
                                trade[0], 'Buy', get_quantity(trade[0], trade[5]))
                list_trades[index] = None
                quantity_used = 0
            elif liste_trade_update[index] != None and list_trades[index] == None:
                list_trades[index] = []
                for trade_update in liste_trade_update[index]:
                    print(
                        f'{list_traders[index][0]} : ouverture d\'une nouvelle position')
                    quantity_used = list_traders[index][2] * \
                        len(liste_trade_update[index])
                    if trade_update[1] == 'Long':
                        qty = open_position(
                            trade_update[0], 'Buy', trade_update[3]*quantity_used)
                        trade_update += [trade_update[3]*quantity_used, qty]
                        indexes_to_add += [
                            liste_trade_update[index].index(trade_update)]
                    elif trade_update[1] == 'Short':
                        qty = open_position(
                            trade_update[0], 'Sell', trade_update[3]*quantity_used)
                        trade_update += [trade_update[3]*quantity_used, qty]
                        indexes_to_add += [
                            liste_trade_update[index].index(trade_update)]
            else:
                for trade in list_trades[index]:
                    similitude = 0
                    for trade_update in liste_trade_update[index]:
                        if trade[0] == trade_update[0]:
                            similitude += 1
                    if similitude == 0:
                        quantity_used = quantity_used-list_traders[index][2]
                        print(
                            f'{list_traders[index][0]} : fermeture d\'une position :')
                        if trade[1] == 'Long':
                            if trade[5] < 0:
                                qty = open_position(trade[0], 'Buy', get_quantity(
                                    trade[0], abs(trade[5])))
                            else:
                                qty = open_position(
                                    trade[0], 'Sell', get_quantity(trade[0], trade[5]))
                        elif trade[1] == 'Short':
                            if trade[5] < 0:
                                qty = open_position(trade[0], 'Sell', get_quantity(
                                    trade[0], abs(trade[5])))
                            else:
                                qty = open_position(
                                    trade[0], 'Buy', get_quantity(trade[0], trade[5]))
                        indexes_to_pop += [list_trades[index].index(trade)]
                for trade_update in liste_trade_update[index]:
                    similitude = 0
                    for trade in list_trades[index]:
                        if trade[0] == trade_update[0]:
                            similitude += 1
                            if trade[2] < trade_update[2]:
                                print((trade, trade_update))
                                print(
                                    f'{list_traders[index][0]} : augmentation d\'une position')
                                augmentation = trade_update[2]/trade[2]
                                if augmentation > 5:
                                    augmentation = 5
                                if trade_update[1] == 'Long':
                                    qty = open_position(
                                        trade[0], 'Buy', (trade[4]*augmentation)-trade[4])
                                    trade[4] = (trade[4]*augmentation)
                                    trade[5] += qty
                                elif trade_update[1] == 'Short':
                                    qty = open_position(
                                        trade[0], 'Sell', (trade[4]*augmentation)-trade[4])
                                    trade[4] = (trade[4]*augmentation)
                                    trade[5] += qty
                                trade[2] = (trade_update.copy())[2]
                            elif trade[2] > trade_update[2]:
                                print((trade, trade_update))
                                print(
                                    f'{list_traders[index][0]} : diminution d\'une position')
                                diminution = trade_update[2]/trade[2]
                                if trade[1] == 'Long':
                                    qty = open_position(
                                        trade[0], 'Sell', abs((trade[4]*diminution)-trade[4]))
                                    trade[4] = (trade[4]*diminution)
                                    trade[5] = trade[5] - qty
                                elif trade[1] == 'Short':
                                    qty = open_position(
                                        trade[0], 'Buy', abs((trade[4]*diminution)-trade[4]))
                                    trade[4] = (trade[4]*diminution)
                                    trade[5] = trade[5] - qty
                                trade[2] = (trade_update.copy())[2]
                    if similitude == 0:
                        print(
                            f'{list_traders[index][0]} : ouverture d\'une nouvelle position')
                        quantity_used += list_traders[index][2]
                        if trade_update[1] == 'Long':
                            qty = open_position(
                                trade_update[0], 'Buy', trade_update[3]*quantity_used)
                            trade_update += [trade_update[3]
                                             * quantity_used, qty]
                            indexes_to_add += [
                                liste_trade_update[index].index(trade_update)]
                        elif trade_update[1] == 'Short':
                            qty = open_position(
                                trade_update[0], 'Sell', trade_update[3]*quantity_used)
                            trade_update += [trade_update[3]
                                             * quantity_used, qty]
                            indexes_to_add += [
                                liste_trade_update[index].index(trade_update)]
            pop_count = 0
            for index_pop in indexes_to_pop:
                print(
                    f'{list_traders[index][0]} : la position suivante a été supprimée :')
                print(list_trades[index][index_pop-pop_count])
                list_trades[index].pop(index_pop-pop_count)
                pop_count += 1
            for index_to_add in indexes_to_add:
                print(
                    f'{list_traders[index][0]} : ajout de la position suivante :')
                print(liste_trade_update[index][index_to_add])
                list_trades[index] += [liste_trade_update[index][index_to_add]]
        os.kill(pointer_id, signal.SIGTERM)

        #display is not active
