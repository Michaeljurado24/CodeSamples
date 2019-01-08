import requests
try:
	from urllib.request import urlretrieve
except:
	from urllib import urlretrieve
from bs4 import BeautifulSoup
import time
import smtplib
import datetime
from delorean import Delorean
from .analyzeModules.StockTime import timeFunctions as timeFunc
from .analyzeModules.StockIO import operations as io
from .analyzeModules.Order import Order, DaySummary
from collections import deque
from sys import stdout
from os import path as PATH
from random import randint, random
"""global vars"""
badCharList = ["$", " ", ",", "X"]
class FakeLock():
	def acquire(self):
		print("no locking mechanism exists to regulate network traffic")
	def release(self):
		print("Danger Danger")
opening = datetime.time(hour = 9, minute = 29, second = 59)


timeMap = {}
current = datetime.datetime(2016,11,11,9,0,0)
for pageNum in range(1,15):
	current = current + datetime.timedelta(minutes = 30)
	timeMap[current.time()] = pageNum
#print timeMap

"""The split website ([returns string data, splitRatio] )"""
def processFutureSplitTr(rawTr):
	rawDataString = rawTr.get_text().encode("ascii", "ignore").strip().decode()
	splitRatio = rawDataString[10:]
	stringSplit = rawDataString[0:10].split("/")
	#goes month-day-year without alteration
	day = stringSplit[1]
	month = stringSplit[0]
	stringSplit[0] =  day #switch day and month
	stringSplit[1] = month
	stringSplit.reverse() #then reverse the list
	return ["-".join(stringSplit), splitRatio]

"""The last sales nasdaq Website data is contained in Tr html elements This method reads the raw
Tr ad produces an Order object"""
def processTrData(rawTr):
	"""takes a rawTr data and converts it to int inputStream
	tr is an html element
	"""
	rawDataString = rawTr.get_text().encode("ascii", "ignore").strip("\n")
	cleanDataString = [x for x in rawDataString if x not in badCharList]
	rawInputStream = cleanDataString.split("\n")
	stringTime  = rawInputStream[0]

	date = timeFunc.getLastTradingDate()
	time = timeFunc.stringToTime(stringTime)

	tradeDate = datetime.datetime(
	date.year,
	date.month,
	date.day,
	time.hour,
	time.minute,
	time.second
	)

	price = float(rawInputStream[1])
	volume = int(rawInputStream[2])

	return Order(price, volume, tradeDate)

"""same  nas urrlib.urlopen but with session"""
def getPageContent(session,url, lock = None):
	if not lock:
		lock = FakeLock()
	lock.acquire()
	content  = session.get(url).content
	lock.release()
	return content
"""A class which handles repeated network requests"""
class NetworkSession():
	def __init__(self, proxyDict = None,
	userAgent = 'Mozilla/5.0 (compatible; AnyApexBot/1.0; +http://www.anyapex.com/bot.html)'):
		self.session = requests.Session()
		#print kfhksdjaf
		if userAgent:
			self.session.headers['User-Agent']  = userAgent
		if proxyDict:
			self.session.proxies.update(proxyDict)

	#"""Returns a list of day Smmaries. Can have any start and end value"""
	def getFullYahooDataList(self, start, end, stock, lock = None):
		if start > end:
			raise Exception("Your start index is after the end date")
		subList = self.getYahooDataList(start, end, stock, lock)
		list_ = subList
		newEnd = end
		while len(subList) >= 90:
			#time.sleep(5)
			newEnd =  list_[0].date - datetime.timedelta(days = 1)
			subList = self.getYahooDataList(start, newEnd, stock, lock)
			list_ = subList + list_
		return list_

	#"""Returns a list of daySummaries for any stock. It can only scape an 100 day window a daySummary gives low, high , mid, open, and close price for a day"""
	def getYahooDataList(self, start, end, stock, lock = None):
		start = Delorean(start, timezone = "UTC").epoch
		end = Delorean(end, timezone = "UTC").epoch
		#could be 1wk, 1d, 1mo

		url = "https://finance.yahoo.com/quote/%s/history?period1=%d&period2=%d&interval=1d&filter=history&frequency=1d" % (stock, start, end)
		pageContent = getPageContent(self.session, url, lock)
		#  print pageContent
		soup = BeautifulSoup(pageContent, "html.parser")

		trList = soup.find("tbody").find_all("tr")
		usefulList = []
		for tr in trList:
			# try:1
			dayDataList = [x.text for x in tr.findAll("span")] #all the data you want except there is hidden chars
			dayDataList = [x.encode("ascii", "ignore").decode() for x in dayDataList]
			daySummary = DaySummary()
			#print(dayDataList)
			daySummary.date = datetime.datetime.strptime(dayDataList[0], '%b %d, %Y')
			if len(dayDataList) <= 2:
				print("There is no data associated with this line")
				for i in dayDataList:
					print((i, "\t"))
				continue
			daySummary.opener = float(dayDataList[1].replace(",", ""))
			daySummary.high = float(dayDataList[2].replace(",", ""))
			daySummary.low = float(dayDataList[3].replace(",", ""))
			daySummary.close = float(dayDataList[4].replace(",", ""))
			#we are skipping the adjust close
			daySummary.volume = int(dayDataList[6].replace(",", ""))
			usefulList.append(daySummary)
		usefulList.reverse()
		return usefulList

	#return sorted(usefulList, key = lambda item: item.date)
	def getYahooDataDaysFromToday(self, daysToGoBack, stock, lock = None):
		scraperFunction = self.getYahooDataList
		if daysToGoBack > 90:
			scraperFunction = self.getFullYahooDataList
		return scraperFunction(datetime.datetime.now() - datetime.timedelta(days = daysToGoBack),
			datetime.datetime.now(), stock, lock = lock)

	"""sends message to myself from future. More instructions will follow"""
	def sellWarning(self, stock, reason):
		server = smtplib.SMTP("smtp.gmail.com:587")
		server.starttls()
		server.ehlo()
		server.login("redacted@gmail.com", "redacted")
		message = """Subject: URGENT sell %s\n
							\rReason: %s.\nMore instructions will follow.
							\rFrom: Future Michael""" % (stock, reason)
		server.sendmail("redacted@gmail.com", "redacted@gmail.com", message)
		server.close()

	"""maybe this will be some useful information like a tabulated list of upcoming splits or something"""
	def infoUpdate(self, infoTitle, info):
		server = smtplib.SMTP("smtp.gmail.com:587")
		server.starttls()
		server.ehlo()
		server.login("redacted@gmail.com", "redacted")
		message = "Subject: %s\n" % infoTitle
		message += info + "\n"
		message += "\rMore Instructions will follow\n"
		message += "\rFrom: Future Michael"
		server.sendmail("redacted@gmail.com", "redacted@gmail.com", message)
		server.close()
	"""Scrpaes share volume for stock"""
	def getShareVolume(self, stock, lock = None):
		url = "http://www.nasdaq.com/symbol/%s"%stock
		while True:
			try:
				pageContent = getPageContent(self.session, url, lock)
				soup = BeautifulSoup(pageContent, "html.parser")
				TableText = soup.find(text = "Share Volume") #row of the table that contains Share Volume
				DivParent = TableText.parent.parent.parent #get its parent, parent, parent
				lastDiv = DivParent.find_all("div")[-1] #the last div contains the volume
				text = lastDiv.get_text() #get the text
				volume = int(text.replace(",", "")) #replace commas with nothing and convert to int
				return volume
			except Exception as ex:
				print(ex)
				print("Problem in get Share Volume")
	def hasWebsite(self, stock, lock = None):
		while True:
			try:
				url = "http://www.nasdaq.com/symbol/%s/real-time" % stock
				time.sleep(random()) #this might help stop errors
				pageContent = getPageContent(self.session, url, lock)
				soup =  BeautifulSoup(pageContent, "html.parser")
				div = soup.find("div", class_ = "notTradingIPO") #does not exist on stocks that are traded
				return not div
			except Exception as E:
				print(("Connection is bad in networking!," , E))
				time.sleep(3600)
				stdout.flush()


	"""gets old splits for stocks. Is a list with most recent on end. """
	def getOldSplits(self, stock, string = True, lock = None):

		url = "https://www.splithistory.com/%s/" % stock.lower()
		goodRequest = False
		while not goodRequest:
			try:
				pageContent = getPageContent(self.session, url, lock)
				goodRequest = True
			except Exception as E:
				print(("Exception in get old splits: ", E))
				time.sleep(2)
		soup =  BeautifulSoup(pageContent, "html.parser")
		html = soup.html
		body = html.body
		center = body.center
		div = center.find("div")
		div  = div.findNextSibling()

		table = div.find("table")
		table = table.findNextSibling().findNextSibling()

		tr = table.find("tr")
		tr = tr.findNextSibling().findNextSibling()

		splitList = []
		if tr == None:
			return splitList
		while tr != None:
			dataList = processFutureSplitTr(tr)
			date = dataList[0]
			if string:
				splitList.append(date)
			else:
				splitList.append(timeFunc.stringToDate(date))
			tr = tr.findNextSibling()
		return splitList

	"""Im not sure if a stock can have multiple future split dates but the closest dates are the first on the list"""
	def getFutureSplitDict(self, string = True, lock = None):
		url = "http://www.nasdaq.com/markets/upcoming-splits.aspx"
		pageContent = getPageContent(self.session, url, lock)
		soup =  BeautifulSoup(pageContent, "html.parser")
		table = soup.find(id = "two_column_main_content_Upcoming_Splits")

		tr = table.find("tr")
		tr = tr.findNextSibling("tr") #first item in table
		splitDict = {}
		while tr: #iterate through table entries
			td = tr.find("td")
			a = td.find("a")
			href = a['href']
			hrefSplit = href.split("/")
			stockName = hrefSplit[-1].encode("ascii", "ignore").upper()
			if not splitDict.__contains__(stockName):
				splitDict[stockName] = []
			splits = splitDict[stockName]

			td = td.findNextSibling()
			splitRatio = td.get_text()

			td = td.findNextSibling() #this gives you payable date
			td = td.findNextSibling()
			rawStringDate = td.get_text().encode("ascii", "ignore").strip()
			splitDate = rawStringDate.split("/")
			day = splitDate[1]
			month = splitDate[0]
			splitDate[0]  = day
			splitDate[1] = month
			splitDate.reverse()
			stringDate = "-".join(splitDate)

			if string == True:
				splits.append(stringDate)
			else:
				splits.append(timeFunc.stringToDate(stringDate))
			tr = tr.findNextSibling()
		return splitDict

	def getFutureDelistDict(self, string = True, lock = None):
		url = "https://listingcenter.nasdaq.com/IssuersPendingSuspensionDelisting.aspx"
		pageContent = getPageContent(self.session, url, lock)
		soup =  BeautifulSoup(pageContent, "html.parser")
		table = soup.find(id = "ctl00_MainContent_gvResults_ctl00")
		tbody = table.find("tbody")
		tr = tbody.find("tr")
		delistDict = {}
		while tr: #iterate through table entries
			tdSplit = tr.find_all("td")
			stockName = tdSplit[1].get_text().encode("ascii", "ignore").strip()

			rawStringDate = tdSplit[4].get_text().encode("ascii", "ignore").strip()
			if rawStringDate:
				splitDate = rawStringDate.split("/")
				day = splitDate[1]
				month = splitDate[0]
				splitDate[0]  = day
				splitDate[1] = month
				splitDate.reverse()
				stringDate = "-".join(splitDate)
				if string:
					delistDict[stockName] = stringDate
				else:
					delistDict[stockName] = timeFunc.stringToDate(stringDate)
			else:
				delistDict[stockName] = datetime.datetime.now() + datetime.timedelta(days = 1)	#will tell it that a split is coming so watch out
			tr = tr.findNextSibling()
		return delistDict

	"""Im not sure if a stock can have multiple future split dates but the closest dates are the first on the list"""
	def getFutureSplits(self, stock, string = True, lock = None):
		splitDict = self.getFutureSplitDict(string, lock = lock)
		stock = stock.lower()
		if not splitDict.__contains__(stock):
			return []
		return splitDict[stock]

	"""
	This only checks the split data: not the lowest day in the database
	Starting date is a string
	Sliding window high is the highest possible sliding Window (int)"""
	def largestSlidingWindow(self, stock, startingDate, slidingWindowHigh, lock = None): #need to check
		oldSplits = self.getOldSplits(stock, False, lock = lock)
		if not oldSplits: #this means it can use a sliding Window stetching back to infinity
			return slidingWindowHigh
		lastSplit = oldSplits[-1]
		startingDate = timeFunc.stringToDate(startingDate)
		if lastSplit > startingDate:
			return -1
		daysCanGoBack = startingDate - lastSplit #
		if daysCanGoBack.days >= slidingWindowHigh:
			return slidingWindowHigh
		return daysCanGoBack.days

	def getPilotList(self, lock = None):
		page = getPageContent(self.session, "https://www.nasdaqtrader.com/Trader.aspx?id=TickPilot", lock = lock)
		soup = BeautifulSoup(page, "html.parser")
		href = soup.find(target = "_blank")["href"]
		page = getPageContent(self.session, href, lock = lock)
		lineSplit = page.split("\n")
		return [x.split("|")[0] for x in lineSplit][1:-2]
	
	def isPilot(self, stock, lock = None):
		return stock in self.getPilotList(lock = lock) #?

	"""last time i checked this did not work"""
	def getBestStockList(self, lock = None):
		while True:
			try:
				pageContent = getPageContent(self.session, "http://www.allpennystocks.com/aps_us/hot_nasdaq_stocks.asp", lock = lock)
				break
			except Exception as E:
				time.sleep(30)
				print(("Penny Stock .com had an error: ", E))
		soup = BeautifulSoup(pageContent, "html.parser")
		tableStruc = soup.find(id = "dataTable")
		tableStruc2 = soup.find(id = "dataTable2")
		def getName(x):
			return x.get_text().encode('ascii', 'ignore').strip()
		return [getName(x) for x in tableStruc.find_all('a')] + [getName(x) for x in tableStruc2.find_all('a')]