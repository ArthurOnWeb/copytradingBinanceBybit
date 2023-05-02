from pybit import usdt_perpetual
from pybit.exceptions import FailedRequestError
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import time as tempo
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from requests.exceptions import RequestException, ConnectionError
import linecache
import tracemalloc
from selenium.webdriver.support import expected_conditions as EC
import pickle


# trying to debug memory leak with tracemalloc
tracemalloc.start()

# displaying debug report


def display_top(snapshot, key_type='lineno', limit=10):
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        print("#%s: %s:%s: %.1f KiB"
              % (index, frame.filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    %s' % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


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
        endpoint="https://api-testnet.bybit.com",
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


def get_trade(link, currency_valables_bybit):
    """
    fonction à modifier car désormais il faut se connecter pour accéder aux trades des autres traders
    j'ai déjà commencé les modifications avec un système ou je récupère les cookies
    """
    # On ouvre le navigateur
    # options = webdriver.EdgeOptions()
    # j'utilise ce profil afin d'être déjà connecté à Binance
    # options.add_argument("disableImageLoading")
    # options.add_argument("disableCaching")
    # options.add_argument("imageQuality")
    # options.add_argument("disableBrowserSecurity")
    # options.add_argument("headless")
    # Récupérer le chemin du profil Chrome actuellement utilisé
    # options = webdriver.ChromeOptions()
    # options.add_argument(
    #     '--user-data-dir=C:\\Users\\33650\\AppData\\Local\\Google\\Chrome\\User Data')
    # options.add_argument(r'--profile-directory=Default')
    # Charger les cookies de session depuis le fichier
    with open('cookies.pkl', 'rb') as f:
        cookies = pickle.load(f)

    # Initialiser le navigateur et ajouter les cookies de session
    driver = webdriver.Chrome()

    # driver = webdriver.Chrome()

    """ Bout de code afin de récuperer les cookies
    # On ouvre la page du trader que l'on veut copier
    driver.get(link)
    tempo.sleep(30)
    
    # Récupérer les cookies de session
    cookies = driver.get_cookies()

    # Sauvegarder les cookies de session dans un fichier
    with open('cookies.pkl', 'wb') as f:
        pickle.dump(cookies, f)
    """
    driver.get(link)
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()
    WebDriverWait(driver, 30).until(EC.presence_of_element_located(
        (By.XPATH, "/html/body/div[1]/div[2]/div[1]/div/div[2]/div/div[2]/div/div[2]/div/div/div/div/table")))

    # on attend que la page charge

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
        return None
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
        driver.close()
        driver.quit()
        return liste_paire


# dernière MAJ 09/01/2023
# currency_valable_bybit = ['10000NFTUSDT', '1000BONKUSDT', '1000BTTUSDT', '1000LUNCUSDT', '1000XECUSDT', '1INCHUSDT', 'AAVEUSDT', 'ACHUSDT', 'ADAUSDT', 'AGLDUSDT', 'AKROUSDT', 'ALGOUSDT', 'ALICEUSDT', 'ALPHAUSDT', 'ANKRUSDT', 'ANTUSDT', 'APEUSDT', 'API3USDT', 'APTUSDT', 'ARPAUSDT', 'ARUSDT', 'ASTRUSDT', 'AUDIOUSDT', 'AVAXUSDT', 'AXSUSDT', 'BAKEUSDT', 'BALUSDT', 'BANDUSDT', 'BATUSDT', 'BCHUSDT', 'BELUSDT', 'BICOUSDT', 'BITUSDT', 'BLZUSDT', 'BNBUSDT', 'BNXUSDT', 'BOBAUSDT', 'BSVUSDT', 'BSWUSDT', 'BTCUSDT', 'C98USDT', 'CEEKUSDT', 'CELOUSDT', 'CELRUSDT', 'CELUSDT', 'CHRUSDT', 'CHZUSDT', 'CKBUSDT', 'COMPUSDT', 'COTIUSDT', 'CREAMUSDT', 'CROUSDT', 'CRVUSDT', 'CTCUSDT', 'CTKUSDT', 'CTSIUSDT', 'CVCUSDT', 'CVXUSDT', 'DARUSDT', 'DASHUSDT', 'DENTUSDT', 'DGBUSDT', 'DODOUSDT', 'DOGEUSDT', 'DOTUSDT', 'DUSKUSDT', 'DYDXUSDT', 'EGLDUSDT', 'ENJUSDT', 'ENSUSDT', 'EOSUSDT', 'ETCUSDT', 'ETHUSDT', 'ETHWUSDT', 'FILUSDT', 'FITFIUSDT', 'FLMUSDT', 'FLOWUSDT', 'FTMUSDT', 'FXSUSDT', 'GALAUSDT', 'GALUSDT', 'GLMRUSDT', 'GMTUSDT', 'GMXUSDT', 'GRTUSDT', 'GTCUSDT', 'HBARUSDT', 'HNTUSDT', 'HOTUSDT',
#                           'ICPUSDT', 'ICXUSDT', 'ILVUSDT', 'IMXUSDT', 'INJUSDT', 'IOSTUSDT', 'IOTAUSDT', 'IOTXUSDT', 'JASMYUSDT', 'JSTUSDT', 'KAVAUSDT', 'KDAUSDT', 'KLAYUSDT', 'KNCUSDT', 'KSMUSDT', 'LDOUSDT', 'LINAUSDT', 'LINKUSDT', 'LITUSDT', 'LOOKSUSDT', 'LPTUSDT', 'LRCUSDT', 'LTCUSDT', 'LUNA2USDT', 'MAGICUSDT', 'MANAUSDT', 'MASKUSDT', 'MATICUSDT', 'MINAUSDT', 'MKRUSDT', 'MTLUSDT', 'NEARUSDT', 'NEOUSDT', 'OCEANUSDT', 'OGNUSDT', 'OMGUSDT', 'ONEUSDT', 'ONTUSDT', 'OPUSDT', 'PAXGUSDT', 'PEOPLEUSDT', 'QNTUSDT', 'QTUMUSDT', 'REEFUSDT', 'RENUSDT', 'REQUSDT', 'RNDRUSDT', 'ROSEUSDT', 'RSRUSDT', 'RSS3USDT', 'RUNEUSDT', 'RVNUSDT', 'SANDUSDT', 'SCRTUSDT', 'SCUSDT', 'SFPUSDT', 'SHIB1000USDT', 'SKLUSDT', 'SLPUSDT', 'SNXUSDT', 'SOLUSDT', 'STGUSDT', 'STMXUSDT', 'STORJUSDT', 'STXUSDT', 'SUNUSDT', 'SUSHIUSDT', 'SWEATUSDT', 'SXPUSDT', 'THETAUSDT', 'TLMUSDT', 'TOMOUSDT', 'TRBUSDT', 'TRXUSDT', 'TWTUSDT', 'UNFIUSDT', 'UNIUSDT', 'USDCUSDT', 'VETUSDT', 'WAVESUSDT', 'WOOUSDT', 'XEMUSDT', 'XLMUSDT', 'XMRUSDT', 'XNOUSDT', 'XRPUSDT', 'XTZUSDT', 'YFIUSDT', 'YGGUSDT', 'ZECUSDT', 'ZENUSDT', 'ZILUSDT', 'ZRXUSDT']


on = True


def bot_final():
    trader1 = str(input('put the link of a trader from Binance :\n'))
    trader2 = str(input('put the link of a trader from Binance :\n'))
    trader3 = str(input('put the link of a trader from Binance :\n'))
    paie_1 = int(
        input('trader 1 : Montant en dollars que vous êtes prêt à payé par positions :\n'))
    paie_2 = int(
        input('trader 2 : Montant en dollars que vous êtes prêt à payé par positions :\n'))
    paie_3 = int(
        input('trader 3 : Montant en dollars que vous êtes prêt à payé par positions :\n'))
    # INITIALISATION
    currency_valables = get_paires_valables()
    time1 = tempo.time()
    # j'ouvre mes positions en fonction de leur proportion chez le trader
    liste_trade1 = get_trade(trader1, currency_valables)
    if liste_trade1 != None:
        quantity_used1 = len(liste_trade1)*paie_1
        for trade1 in liste_trade1:
            if trade1[1] == 'Long':
                print('trader1 : INITIALISATION')
                qty = open_position(trade1[0], 'Buy', trade1[3]*quantity_used1)
                trade1 += [trade1[3]*quantity_used1, qty]
            elif trade1[1] == 'Short':
                print('trader1 : INITIALISATION')
                qty = open_position(
                    trade1[0], 'Sell', trade1[3]*quantity_used1)
                trade1 += [trade1[3]*quantity_used1, qty]
        print(
            f"temps d'initialisation pour trader1 : {tempo.time()-time1} secondes")
    liste_trade2 = get_trade(trader2, currency_valables)
    if liste_trade2 != None:
        quantity_used2 = len(liste_trade2)*paie_2
        for trade2 in liste_trade2:
            if trade2[1] == 'Long':
                print('trader2 : INITIALISATION')
                qty = open_position(trade2[0], 'Buy', trade2[3]*quantity_used2)
                trade2 += [trade2[3]*quantity_used2, qty]
            elif trade2[1] == 'Short':
                print('trader 2 : INITIALISATION')
                qty = open_position(
                    trade2[0], 'Sell', trade2[3]*quantity_used2)
                trade2 += [trade2[3]*quantity_used2, qty]
    liste_trade3 = get_trade(trader3, currency_valables)
    if liste_trade3 != None:
        quantity_used3 = len(liste_trade3)*paie_3
        for trade3 in liste_trade3:
            if trade3[1] == 'Long':
                print('trader3 : INITIALISATION')
                qty = open_position(trade3[0], 'Buy', trade3[3]*quantity_used3)
                trade3 += [trade3[3]*quantity_used3, qty]
            elif trade3[1] == 'Short':
                print('trader 3 : INITIALISATION')
                qty = open_position(
                    trade3[0], 'Sell', trade3[3]*quantity_used3)
                trade3 += [trade3[3]*quantity_used3, qty]

    # FONCTIONNEMENT
    liste_trade1_update = None
    liste_trade2_update = None
    liste_trade3_update = None
    compteur_passage = 0
    while on == True:

        compteur_passage += 1
        if compteur_passage % 600 == 0:
            currency_valables = get_paires_valables()
            print(f'trader1 :{liste_trade1}')
            print(f'trader2 :{liste_trade2}')
            print(f'trader3 :{liste_trade3}')
        indexes_to_pop1 = []
        indexes_to_add1 = []
        try:
            liste_trade1_update = get_trade(trader1, currency_valables)
        except TimeoutException:
            tempo.sleep(10)
            print('Une erreur de type TimeoutException est survenue'+tempo.ctime())
        except NoSuchElementException:
            tempo.sleep(10)
            print('une erreur de type NoSuchElement est survenue'+tempo.ctime())
        except WebDriverException:
            tempo.sleep(10)
            print('Une erreur de type WebDriverException est survenue'+tempo.ctime())
            if compteur_passage % 5 == 0:
                open_position('BIT', 'Buy', 0.01)
            snapshot = tracemalloc.take_snapshot()
            display_top(snapshot)
        except RequestException:
            tempo.sleep(10)
            print('Une erreur de type RequestException est survenue'+tempo.ctime())
        except ConnectionError:
            tempo.sleep(10)
            print('Une erreur de type ConnectionError est survenue'+tempo.ctime())
        except FailedRequestError:
            print('Une erreur de type FailedRequestError est survenue'+tempo.ctime())
            tempo.sleep(1801)
        if liste_trade1_update == None and liste_trade1 == None:
            pass
        elif liste_trade1_update == liste_trade1:
            pass
        elif liste_trade1_update == None:
            print('fermeture des trades du trader1 '+trader1)
            for trade1 in liste_trade1:
                if trade1[1] == 'Long':
                    if trade1[5] < 0:
                        qty = open_position(trade1[0], 'Buy', get_quantity(
                            trade1[0], abs(trade1[5])))
                    else:
                        qty = open_position(
                            trade1[0], 'Sell', get_quantity(trade1[0], trade1[5]))
                elif trade1[1] == 'Short':
                    if trade1[5] < 0:
                        qty = open_position(trade1[0], 'Sell', get_quantity(
                            trade1[0], abs(trade1[5])))
                    else:
                        qty = open_position(
                            trade1[0], 'Buy', get_quantity(trade1[0], trade1[5]))
            liste_trade1 = None
            quantity_used1 = 0
        elif liste_trade1_update != None and liste_trade1 == None:
            liste_trade1 = []
            for trade1_update in liste_trade1_update:
                print('trader 1 : ouverture d\'une nouvelle position')
                quantity_used1 = paie_1*len(liste_trade1_update)
                if trade1_update[1] == 'Long':
                    qty = open_position(
                        trade1_update[0], 'Buy', trade1_update[3]*quantity_used1)
                    trade1_update += [trade1_update[3]*quantity_used1, qty]
                    indexes_to_add1 += [
                        liste_trade1_update.index(trade1_update)]
                elif trade1_update[1] == 'Short':
                    qty = open_position(
                        trade1_update[0], 'Sell', trade1_update[3]*quantity_used1)
                    trade1_update += [trade1_update[3]*quantity_used1, qty]
                    indexes_to_add1 += [
                        liste_trade1_update.index(trade1_update)]
        else:
            for trade1 in liste_trade1:
                similitude = 0
                for trade1_update in liste_trade1_update:
                    if trade1[0] == trade1_update[0]:
                        similitude += 1
                if similitude == 0:
                    quantity_used1 = quantity_used1-paie_1
                    print('trader 1 : fermeture d\'une position :')
                    if trade1[1] == 'Long':
                        if trade1[5] < 0:
                            qty = open_position(trade1[0], 'Buy', get_quantity(
                                trade1[0], abs(trade1[5])))
                        else:
                            qty = open_position(
                                trade1[0], 'Sell', get_quantity(trade1[0], trade1[5]))
                    elif trade1[1] == 'Short':
                        if trade1[5] < 0:
                            qty = open_position(trade1[0], 'Sell', get_quantity(
                                trade1[0], abs(trade1[5])))
                        else:
                            qty = open_position(
                                trade1[0], 'Buy', get_quantity(trade1[0], trade1[5]))
                    indexes_to_pop1 += [liste_trade1.index(trade1)]
            for trade1_update in liste_trade1_update:
                similitude = 0
                for trade1 in liste_trade1:
                    if trade1[0] == trade1_update[0]:
                        similitude += 1
                        if trade1[2] < trade1_update[2]:
                            print((trade1, trade1_update))
                            print('trader 1 : augmentation d\'une position')
                            augmentation = trade1_update[2]/trade1[2]
                            if augmentation > 5:
                                augmentation = 5
                            if trade1_update[1] == 'Long':
                                qty = open_position(
                                    trade1[0], 'Buy', (trade1[4]*augmentation)-trade1[4])
                                trade1[4] = (trade1[4]*augmentation)
                                trade1[5] += qty
                            elif trade1_update[1] == 'Short':
                                qty = open_position(
                                    trade1[0], 'Sell', (trade1[4]*augmentation)-trade1[4])
                                trade1[4] = (trade1[4]*augmentation)
                                trade1[5] += qty
                            trade1[2] = (trade1_update.copy())[2]
                        elif trade1[2] > trade1_update[2]:
                            print((trade1, trade1_update))
                            print('trader 1 : diminution d\'une position')
                            diminution = trade1_update[2]/trade1[2]
                            if trade1[1] == 'Long':
                                qty = open_position(
                                    trade1[0], 'Sell', abs((trade1[4]*diminution)-trade1[4]))
                                trade1[4] = (trade1[4]*diminution)
                                trade1[5] = trade1[5] - qty
                            elif trade1[1] == 'Short':
                                qty = open_position(
                                    trade1[0], 'Buy', abs((trade1[4]*diminution)-trade1[4]))
                                trade1[4] = (trade1[4]*diminution)
                                trade1[5] = trade1[5] - qty
                            trade1[2] = (trade1_update.copy())[2]
                if similitude == 0:
                    print('trader 1 : ouverture d\'une nouvelle position')
                    quantity_used1 += paie_1
                    if trade1_update[1] == 'Long':
                        qty = open_position(
                            trade1_update[0], 'Buy', trade1_update[3]*quantity_used1)
                        trade1_update += [trade1_update[3]*quantity_used1, qty]
                        indexes_to_add1 += [
                            liste_trade1_update.index(trade1_update)]
                    elif trade1_update[1] == 'Short':
                        qty = open_position(
                            trade1_update[0], 'Sell', trade1_update[3]*quantity_used1)
                        trade1_update += [trade1_update[3]*quantity_used1, qty]
                        indexes_to_add1 += [
                            liste_trade1_update.index(trade1_update)]
        pop_count = 0
        for index in indexes_to_pop1:
            print('trader 1 : la position suivante a été supprimée :')
            print(liste_trade1[index-pop_count])
            liste_trade1.pop(index-pop_count)
            pop_count += 1
        for index in indexes_to_add1:
            print('trader 1 : ajout de la position suivante :')
            print(liste_trade1_update[index])
            liste_trade1 += [liste_trade1_update[index]]
        indexes_to_pop2 = []
        indexes_to_add2 = []
        try:
            liste_trade2_update = get_trade(trader2, currency_valables)
        except TimeoutException:
            tempo.sleep(10)
            print('Une erreur de type TimeoutException est survenue'+tempo.ctime())
        except WebDriverException:
            tempo.sleep(10)
            print('Une erreur de type WebDriverException est survenue'+tempo.ctime())
        except NoSuchElementException:
            tempo.sleep(10)
            print('une erreur de type NoSuchElement est survenue'+tempo.ctime())
        except RequestException:
            tempo.sleep(10)
            print('Une erreur de type RequestException est survenue'+tempo.ctime())
        except ConnectionError:
            tempo.sleep(10)
            print('Une erreur de type ConnectionError est survenue'+tempo.ctime())
        except FailedRequestError:
            print('Une erreur de type FailedRequestError est survenue'+tempo.ctime())
            tempo.sleep(1801)
        if liste_trade2_update == None and liste_trade2 == None:
            pass
        elif liste_trade2_update == liste_trade2:
            pass
        elif liste_trade2_update == None:
            print('fermeture des trades du trader2 '+trader2)
            for trade2 in liste_trade2:
                if trade2[1] == 'Long':
                    if trade2[5] < 0:
                        qty = open_position(trade2[0], 'Buy', get_quantity(
                            trade2[0], abs(trade2[5])))
                    else:
                        qty = open_position(
                            trade2[0], 'Sell', get_quantity(trade2[0], trade2[5]))
                elif trade2[1] == 'Short':
                    if trade2[5] < 0:
                        qty = open_position(trade2[0], 'Sell', get_quantity(
                            trade2[0], abs(trade2[5])))
                    else:
                        qty = open_position(
                            trade2[0], 'Buy', get_quantity(trade2[0], trade2[5]))
            liste_trade2 = None
            quantity_used2 = 0
        elif liste_trade2_update != None and liste_trade2 == None:
            liste_trade2 = []
            for trade2_update in liste_trade2_update:
                print('trader 2 : ouverture d\'une nouvelle position')
                quantity_used2 = paie_2*len(liste_trade2_update)
                if trade2_update[1] == 'Long':
                    qty = open_position(
                        trade2_update[0], 'Buy', trade2_update[3]*quantity_used2)
                    trade2_update += [trade2_update[3]*quantity_used2, qty]
                    indexes_to_add2 += [
                        liste_trade2_update.index(trade2_update)]
                elif trade2_update[1] == 'Short':
                    qty = open_position(
                        trade2_update[0], 'Sell', trade2_update[3]*quantity_used2)
                    trade2_update += [trade2_update[3]*quantity_used2, qty]
                    indexes_to_add2 += [
                        liste_trade2_update.index(trade2_update)]
        else:
            for trade2 in liste_trade2:
                similitude = 0
                for trade2_update in liste_trade2_update:
                    if trade2[0] == trade2_update[0]:
                        similitude += 1
                if similitude == 0:
                    quantity_used2 = quantity_used2-paie_2
                    print('trader 2 : fermeture d\'une position :')
                    if trade2[1] == 'Long':
                        if trade2[5] < 0:
                            qty = open_position(trade2[0], 'Buy', get_quantity(
                                trade2[0], abs(trade2[5])))
                        else:
                            qty = open_position(
                                trade2[0], 'Sell', get_quantity(trade2[0], trade2[5]))
                    elif trade2[1] == 'Short':
                        if trade2[5] < 0:
                            qty = open_position(trade2[0], 'Sell', get_quantity(
                                trade2[0], abs(trade2[5])))
                        else:
                            qty = open_position(
                                trade2[0], 'Buy', get_quantity(trade2[0], trade2[5]))
                    indexes_to_pop2 += [liste_trade2.index(trade2)]
            for trade2_update in liste_trade2_update:
                similitude = 0
                for trade2 in liste_trade2:
                    if trade2[0] == trade2_update[0]:
                        similitude += 1
                        if trade2[2] < trade2_update[2]:
                            print((trade2, trade2_update))
                            print('trader 2 : augmentation d\'une position')
                            augmentation = trade2_update[2]/trade2[2]
                            if augmentation > 5:
                                augmentation = 5
                            if trade2_update[1] == 'Long':
                                qty = open_position(
                                    trade2[0], 'Buy', (trade2[4]*augmentation)-trade2[4])
                                trade2[4] = (trade2[4]*augmentation)
                                trade2[5] += qty
                            elif trade2_update[1] == 'Short':
                                qty = open_position(
                                    trade2[0], 'Sell', (trade2[4]*augmentation)-trade2[4])
                                trade2[4] = (trade2[4]*augmentation)
                                trade2[5] += qty
                            trade2[2] = (trade2_update.copy())[2]
                        elif trade2[2] > trade2_update[2]:
                            print((trade2, trade2_update))
                            print('trader 2 : diminution d\'une position')
                            diminution = trade2_update[2]/trade2[2]
                            if trade2[1] == 'Long':
                                qty = open_position(
                                    trade2[0], 'Sell', abs((trade2[4]*diminution)-trade2[4]))
                                trade2[4] = (trade2[4]*diminution)
                                trade2[5] = trade2[5]-qty
                            elif trade2[1] == 'Short':
                                qty = open_position(
                                    trade2[0], 'Buy', abs((trade2[4]*diminution)-trade2[4]))
                                trade2[4] = (trade2[4]*diminution)
                                trade2[5] = trade2[5]-qty
                            trade2[2] = (trade2_update.copy())[2]
                if similitude == 0:
                    print('trader 2 : ouverture d\'une nouvelle position')
                    quantity_used2 += paie_2
                    if trade2_update[1] == 'Long':
                        qty = open_position(
                            trade2_update[0], 'Buy', trade2_update[3]*quantity_used2)
                        trade2_update += [trade2_update[3]*quantity_used2, qty]
                        indexes_to_add2 += [
                            liste_trade2_update.index(trade2_update)]
                    elif trade2_update[1] == 'Short':
                        qty = open_position(
                            trade2_update[0], 'Sell', trade2_update[3]*quantity_used2)
                        trade2_update += [trade2_update[3]*quantity_used2, qty]
                        indexes_to_add2 += [
                            liste_trade2_update.index(trade2_update)]
        pop_count = 0
        for index in indexes_to_pop2:
            print('trader 2 : la position suivante a été supprimée :')
            print(liste_trade2[index-pop_count])
            liste_trade2.pop(index-pop_count)
            pop_count += 1
        for index in indexes_to_add2:
            print('trader 2 : ajout de la position suivante :')
            print(liste_trade2_update[index])
            liste_trade2 += [liste_trade2_update[index]]
        indexes_to_pop3 = []
        indexes_to_add3 = []
        try:
            liste_trade3_update = get_trade(trader3, currency_valables)
        except TimeoutException:
            tempo.sleep(10)
            print('Une erreur de type TimeoutException est survenue'+tempo.ctime())
        except WebDriverException:
            tempo.sleep(10)
            print('Une erreur de type WebDriverException est survenue'+tempo.ctime())
            if compteur_passage % 5 == 0:
                open_position('BIT', 'Sell', 0.01)
        except NoSuchElementException:
            tempo.sleep(10)
            print('une erreur de type NoSuchElement est survenue'+tempo.ctime())
        except RequestException:
            tempo.sleep(10)
            print('Une erreur de type RequestException est survenue'+tempo.ctime())
        except ConnectionError:
            tempo.sleep(10)
            print('Une erreur de type ConnectionError est survenue'+tempo.ctime())
        except FailedRequestError:
            print('Une erreur de type FailedRequestError est survenue'+tempo.ctime())
            tempo.sleep(1801)
        if liste_trade3_update == None and liste_trade3 == None:
            pass
        elif liste_trade3_update == liste_trade3:
            pass
        elif liste_trade3_update == None:
            print('fermeture des trades du trader3 '+trader3)
            for trade3 in liste_trade3:
                if trade3[1] == 'Long':
                    if trade3[5] < 0:
                        qty = open_position(trade3[0], 'Buy', get_quantity(
                            trade3[0], abs(trade3[5])))
                    else:
                        qty = open_position(
                            trade3[0], 'Sell', get_quantity(trade3[0], trade3[5]))
                elif trade3[1] == 'Short':
                    if trade3[5] < 0:
                        qty = open_position(trade3[0], 'Sell', get_quantity(
                            trade3[0], abs(trade3[5])))
                    else:
                        qty = open_position(
                            trade3[0], 'Buy', get_quantity(trade3[0], trade3[5]))
            liste_trade3 = None
            quantity_used3 = 0
        elif liste_trade3_update != None and liste_trade3 == None:
            liste_trade3 = []
            for trade3_update in liste_trade3_update:
                print('trader 3 : ouverture d\'une nouvelle position')
                quantity_used3 = paie_3*len(liste_trade3_update)
                if trade3_update[1] == 'Long':
                    qty = open_position(
                        trade3_update[0], 'Buy', trade3_update[3]*quantity_used3)
                    trade3_update += [trade3_update[3]*quantity_used3, qty]
                    indexes_to_add3 += [
                        liste_trade3_update.index(trade3_update)]
                elif trade3_update[1] == 'Short':
                    qty = open_position(
                        trade3_update[0], 'Sell', trade3_update[3]*quantity_used3)
                    trade3_update += [trade3_update[3]*quantity_used3, qty]
                    indexes_to_add3 += [
                        liste_trade3_update.index(trade3_update)]
        else:
            for trade3 in liste_trade3:
                similitude = 0
                for trade3_update in liste_trade3_update:
                    if trade3[0] == trade3_update[0]:
                        similitude += 1
                if similitude == 0:
                    quantity_used3 = quantity_used3-paie_3
                    print('trader 3 : fermeture d\'une position :')
                    if trade3[1] == 'Long':
                        if trade3[5] < 0:
                            qty = open_position(trade3[0], 'Buy', get_quantity(
                                trade3[0], abs(trade3[5])))
                        else:
                            qty = open_position(
                                trade3[0], 'Sell', get_quantity(trade3[0], trade3[5]))
                    elif trade3[1] == 'Short':
                        if trade3[5] < 0:
                            qty = open_position(trade3[0], 'Sell', get_quantity(
                                trade3[0], abs(trade3[5])))
                        else:
                            qty = open_position(
                                trade3[0], 'Buy', get_quantity(trade3[0], trade3[5]))
                    indexes_to_pop3 += [liste_trade3.index(trade3)]
            for trade3_update in liste_trade3_update:
                similitude = 0
                for trade3 in liste_trade3:
                    if trade3[0] == trade3_update[0]:
                        similitude += 1
                        if trade3[2] < trade3_update[2]:
                            print((trade3, trade3_update))
                            print('trader 3 : augmentation d\'une position')
                            augmentation = trade3_update[2]/trade3[2]
                            if augmentation > 5:
                                augmentation = 5
                            if trade3_update[1] == 'Long':
                                qty = open_position(
                                    trade3[0], 'Buy', (trade3[4]*augmentation)-trade3[4])
                                trade3[4] = (trade3[4]*augmentation)
                                trade3[5] += qty
                            elif trade3_update[1] == 'Short':
                                qty = open_position(
                                    trade3[0], 'Sell', (trade3[4]*augmentation)-trade3[4])
                                trade3[4] = (trade3[4]*augmentation)
                                trade3[5] += qty
                            trade3[2] = (trade3_update.copy())[2]
                        elif trade3[2] > trade3_update[2]:
                            print((trade3, trade3_update))
                            print('trader 3 : diminution d\'une position')
                            diminution = trade3_update[2]/trade3[2]
                            if trade3[1] == 'Long':
                                qty = open_position(
                                    trade3[0], 'Sell', abs((trade3[4]*diminution)-trade3[4]))
                                trade3[4] = (trade3[4]*diminution)
                                trade3[5] = trade3[5]-qty
                            elif trade3[1] == 'Short':
                                qty = open_position(
                                    trade3[0], 'Buy', abs((trade3[4]*diminution)-trade3[4]))
                                trade3[4] = (trade3[4]*diminution)
                                trade3[5] = trade3[5]-qty
                            trade3[2] = (trade3_update.copy())[2]
                if similitude == 0:
                    print('trader 3 : ouverture d\'une nouvelle position')
                    quantity_used3 += paie_3
                    if trade3_update[1] == 'Long':
                        qty = open_position(
                            trade3_update[0], 'Buy', trade3_update[3]*quantity_used3)
                        trade3_update += [trade3_update[3]*quantity_used3, qty]
                        indexes_to_add3 += [
                            liste_trade3_update.index(trade3_update)]
                    elif trade3_update[1] == 'Short':
                        qty = open_position(
                            trade3_update[0], 'Sell', trade3_update[3]*quantity_used3)
                        trade3_update += [trade3_update[3]*quantity_used3, qty]
                        indexes_to_add3 += [
                            liste_trade3_update.index(trade3_update)]
        pop_count = 0
        for index in indexes_to_pop3:
            print('trader 3 : la position suivante a été supprimée :')
            print(liste_trade3[index-pop_count])
            liste_trade3.pop(index-pop_count)
            pop_count += 1
        for index in indexes_to_add3:
            print('trader 3 : ajout de la position suivante :')
            print(liste_trade3_update[index])
            liste_trade3 += [liste_trade3_update[index]]


if __name__ == '__main__':
    bot_final()

# trader testable : Bear_grizly = "https://www.binance.com/en/futures-activity/leaderboard/user?encryptedUid=FAD84AAFD6E43900BF15E06B21857715"
