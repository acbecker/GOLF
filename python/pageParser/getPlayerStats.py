from bs4 import BeautifulSoup
import posixpath
import urllib 
from urlparse import urlsplit

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
        raise IOError("Couldn't find %s"%(path))
    return pagestr

def sanitizeEntry(entry):
    els = entry.split()
    return "_".join([el.lower() for el in els])

BASEURL = "http://espn.go.com"

class pageParser(object):
    def __init__(self, url="http://espn.go.com/golf/players", contentParser=urllib.urlopen, urlSanitizer=lambda x:x):
        self.url = url
        self.playerMd = {}
        trlist = self.get_page()
        for chunk in chunks(trlist[1:-1], 50):
            nchunk = [trlist[0],]+chunk+[trlist[-1],]
            pagestr = "</tr>\n".join(nchunk)
            self.page = BeautifulSoup(pagestr)
            self.rows = self.get_player_entries()
            self.playerMd.update(self.get_player_md())
        self.playerInfo = self.get_player_info(contentParser, urlSanitizer)
        self.activeKey = None

    def get_page(self):
        #response = urllib.urlopen(self.url)
        fh = open('data/espn_players.html')
        pagestr = unicode()
        for l in fh:
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
            playerMd[playerKey] = playerDict
        return playerMd

    def loop_through_tournaments(self, url, contentParser, urlSanitizer):
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
        except:
            pass 
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
                                path = splitUrl(turl)
                                ididx = path.index('id')
                                tididx = path.index('tournamentId')
                                print path, ididx, tididx
                                print path[ididx-1], path[tididx-1], rnd
                                self.parse_round(rdiv)

    def parse_round(self, div):
        trs = div.find_all('tr')
        if len(trs) == 6: #In 4th round
            trs = trs[2:]
        elif len(trs) == 5: #In another round
            trs = trs[1:]
        for txt, score in zip(trs[0].find_all('td')[1:], trs[1].find_all('td')[1:]):
            print " ".join([ss for ss in txt.stripped_strings]), score.text
        for txt, score in zip(trs[2].find_all('td')[1:], trs[3].find_all('td')[1:]):
            print " ".join([ss for ss in txt.stripped_strings]), score.text

    def get_player_info(self, contentParser, urlSanitizer):
        retDict = {}
        for k in self.playerMd:
            self.activeKey = k
            retDict[k] = {}
            #response = urllib.urlopen(self.playerMd[k]['playerLink'])
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
                        #print infoKey, valtxt
            lis = page.find_all('li')
            url = None
            for li in lis:
                if li.text == "Scorecards":
                    url = li.a['href']
            self.loop_through_tournaments(BASEURL+url, contentParser, urlSanitizer)
        return retDict

def parseUrlToPath(url):
    parsedUrl = urlsplit(url)
    return 'data'+parsedUrl.path
pp = pageParser(contentParser=readHtmlFile, urlSanitizer=parseUrlToPath)
for k in pp.playerMd:
    print pp.playerMd[k]['playerLink']
