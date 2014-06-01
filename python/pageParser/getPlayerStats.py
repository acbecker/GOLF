from bs4 import BeautifulSoup
import sqlite3
import posixpath
import urllib 
from urlparse import urlsplit
from datetime import date, timedelta
import warnings

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def readHtmlFile(path):
    try:
        fh = open(path)
        pagestr = "".join(fh.readlines())
    except IOError:
        #raise IOError("Couldn't find %s"%(path))
        warnings.warn("Couldn't find %s"%(path))
        pagestr = ""
    return pagestr

def sanitizeEntry(entry):
    els = entry.split()
    return "_".join([el.lower() for el in els])

BASEURL = "http://espn.go.com"

class pageParser(object):
    def __init__(self, url="http://espn.go.com/golf/players", contentParser=urllib.urlopen, urlSanitizer=lambda x:x, dbname='golf.sqlite'):
        self.dbConn = self.make_db(dbname)
        self.playerMd = {}
        self.tournaments = {}
        trlist = self.get_page(url, contentParser, urlSanitizer)
        for chunk in chunks(trlist[1:-1], 50):
            nchunk = [trlist[0],]+chunk+[trlist[-1],]
            pagestr = "</tr>\n".join(nchunk)
            self.page = BeautifulSoup(pagestr)
            self.rows = self.get_player_entries()
            self.playerMd.update(self.get_player_md())
        for k in self.playerMd:
            self.dbConn.execute('insert into player values (?,?,?,?)', (int(k), self.playerMd[k]['playerName'],
                                 self.playerMd[k]['playerCountry'], self.playerMd[k]['playerLink']))
        self.playerInfo = self.get_player_info(contentParser, urlSanitizer)
        for k in self.tournaments:
            self.dbConn.execute('insert into tourn values (?,?,?,?)', (k, self.tournaments[k]['tournName'],
                                 self.tournaments[k]['beginDate'], self.tournaments[k]['endDate']))
        self.dbConn.commit()
        self.activeKey = None

    @staticmethod
    def make_db(dbname):
        dbConn = sqlite3.connect(dbname)
        dbConn.execute('''CREATE TABLE player (playerId int, playerName text, playerCountry text, playerLink text)''')
        dbConn.execute('''CREATE TABLE tourn (tournId int, tournName text, begDate text, endDate text)''')
        dbConn.execute('''CREATE TABLE scores (playerId int, tournId int, roundId int, hole int, score int, 
                               par int, length int, coursename text, date DATETIME)''')
        dbConn.commit()
        return dbConn

    @staticmethod
    def get_page(url, contentParser, urlSanitizer):
        #response = urllib.urlopen(self.url)
        #fh = open('data/espn_players.html')
        response = contentParser(urlSanitizer(url))
        for l in response.split("\n"):
            els = l.split('</tr>')
            if len(els) > 1:
                return els

    def get_player_entries(self):
        div = self.page.find(id='my-players-table')
        table = div.table
        trlist = table.find_all('tr')
        rows = []
        for tr in trlist:
            if tr['class'][0] in ('evenrow', 'oddrow'):
                rows.append(tr)
        return rows

    def get_player_md(self):
        playerMd = {}
        for row in self.rows:
            playerDict = {}
            playerKey = (row['class'][1].split('-'))[-1]
            link, country = row.find_all('td')
            playerDict['playerCountry']= country.get_text()
            playerDict['playerLink'] = link.a['href']
            playerDict['playerName'] = row.find('a').text
            playerMd[playerKey] = playerDict
        return playerMd

    @staticmethod
    def parse_date(datestr):
        monthdict = dict([(m, i+1) for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                                        'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])])
        month, daterange, yr = datestr.split()
        mindex = monthdict[month.lower()]
        days = daterange.split('-')
        #evidently there are one day tournaments
        if len(days) == 1:
            bday = days[0][:-1]
            eday = days[0][:-1]
        else:
            bday = days[0]
            #clip comma off end
            eday = days[1][:-1]
        bday = int(bday)
        eday = int(eday)
        yr = int(yr)
        return date(yr, mindex, bday), date(yr, mindex, eday)

    def loop_through_tournaments(self, url, contentParser, urlSanitizer, fileHandle=None):
        def splitUrl(url):
            returl = []
            while url:
                p, tip = posixpath.split(url)
                returl.append(tip)
                url = p
            return returl

        if url is None:
            return
        url = urlSanitizer(url)
        try:
            response = contentParser(url)
        #We may be missing urls
        except:
            print url
            return
        page = BeautifulSoup(response)
        sels = page.find_all('select')
        yrUrls = {}
        for sel in sels:
            if 'name' in sel.attrs and sel['name'] == 'years':
                opts = sel.find_all('option')
                for opt in opts:
                    try:
                        yrUrls[int(opt.text)] = opt['value']
                    except ValueError:
                        #Ignore entries that don't correspond to an int year
                        continue
        for k in yrUrls:
            try:
                response = contentParser(urlSanitizer(yrUrls[k]))
            except:
                continue
            ypage = BeautifulSoup(response)
            sels = ypage.find_all('select')
            for sel in sels:
                if 'name' in sel.attrs and sel['name'] == 'tournaments':
                    opts = sel.find_all('option')
                    for opt in opts:
                        if not opt['value']:
                            continue
                        try:
                            response = contentParser(urlSanitizer(opt['value']))
                        except:
                            continue
                        turl = urlSanitizer(opt['value'])
                        tpage = BeautifulSoup(response)
                        for rnd in (1,2,3,4):
                            rdiv = tpage.find(id='round-%i-%s'%(rnd, self.activeKey))
                            if rdiv:
                                _ = tpage.find('h3').text
                                course = tpage.find('h3').find_next().text
                                els = _.split(' - ')
                                tourn = ' - '.join(els[:-1])
                                begdate, enddate = self.parse_date(els[-1])
                                path = splitUrl(turl)
                                ididx = path.index('id')
                                tididx = path.index('tournamentId')
                                playerId = path[ididx-1]
                                tournId = path[tididx-1]
                                self.tournaments.update({tournId:{'tournName':tourn, 'beginDate':begdate, 'endDate':enddate}})
                                scores = self.parse_round(rdiv)
                                insrt = []
                                for i in range(1, 19):
                                    insrt.append((playerId, tournId, rnd, i, scores[i]['score'], scores[i]['par'],
                                                  scores[i]['length'], course, begdate+timedelta(days=rnd-1)))
                                self.insertScores(insrt)

    def insertScores(self, insarr):
        self.dbConn.executemany('insert into scores values(?,?,?,?,?,?,?,?,?)', insarr)
        self.dbConn.commit()

    @staticmethod
    def catchBadVals(val):
        try:
            retval = int(val)
        except ValueError:
            retval = -1
        return retval

    def parse_round(self, div):
        trs = div.find_all('tr')
        if len(trs) == 6: #In 4th round
            trs = trs[2:]
        elif len(trs) == 5: #In another round
            trs = trs[1:]
        scores = {}
        #Front nine
        for txt, score in zip(trs[0].find_all('td')[1:], trs[1].find_all('td')[1:]):
            stlist = [ss for ss in txt.stripped_strings]
            if stlist[0].lower() in ('in', 'out'):
                continue
            scores[int(stlist[0])] = {'length':self.catchBadVals(stlist[1]), 'par':self.catchBadVals(stlist[2]), 'score':self.catchBadVals(score.text)} 
        #Back nine
        for txt, score in zip(trs[2].find_all('td')[1:], trs[3].find_all('td')[1:]):
            stlist = [ss for ss in txt.stripped_strings]
            if stlist[0].lower() in ('in', 'out'):
                continue
            scores[int(stlist[0])] = {'length':self.catchBadVals(stlist[1]), 'par':self.catchBadVals(stlist[2]), 'score':self.catchBadVals(score.text)} 
        return scores

    def get_player_info(self, contentParser, urlSanitizer):
        retDict = {}
        for k in self.playerMd:
            self.activeKey = k
            retDict[k] = {}
            #pname = self.playerMd[k]['playerLink'].split("/")[-1]
            response = contentParser(urlSanitizer(self.playerMd[k]['playerLink']))
            page = BeautifulSoup(response)
            uls = page.find_all('ul')
            for ul in uls:
                if 'class' in ul.attrs and ul.attrs['class'][0] == 'player-metadata':
                    lis = ul.find_all('li')
                    for li in lis:
                        infoKey = li.span.text
                        valtxt = li.text
                        valtxt = valtxt.lstrip(infoKey)
                        infoKey = sanitizeEntry(infoKey)
                        retDict[k][infoKey] = valtxt
            lis = page.find_all('li')
            url = None
            for li in lis:
                if li.text == "Scorecards":
                    url = li.a['href']
            if url:
                self.loop_through_tournaments(BASEURL+url, contentParser, urlSanitizer)
        return retDict

def parseUrlToPath(url):
    parsedUrl = urlsplit(url)
    return 'data'+parsedUrl.path
pp = pageParser(contentParser=readHtmlFile, urlSanitizer=parseUrlToPath)
for k in pp.playerMd:
    print pp.playerMd[k]['playerLink']
