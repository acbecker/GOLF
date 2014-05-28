from bs4 import BeautifulSoup
import urllib 
from urlparse import urlsplit

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def readHtmlFile(path):
    fh = open(path)
    try:
        pagestr = "".join(fh.readlines())
    finally:
        fh.close()
    return pagestr

def sanitizeEntry(entry):
    els = entry.split()
    return "_".join([el.lower() for el in els])

BASEURL = "http://espn.go.com"

class pageParser(object):
    def __init__(self, url="http://espn.go.com/golf/players"):
        self.url = url
        self.playerMd = {}
        trlist = self.get_page()
        for chunk in chunks(trlist[1:-1], 50):
            nchunk = [trlist[0],]+chunk+[trlist[-1],]
            pagestr = "</tr>\n".join(nchunk)
            self.page = BeautifulSoup(pagestr)
            self.rows = self.get_player_entries()
            self.playerMd.update(self.get_player_md())
        self.playerInfo = self.get_player_info()
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

    def loop_through_tournaments(self, url):
        if url is None:
            return
        response = urllib.urlopen(url)
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
            print "year", yrUrls[k]
            response = urllib.urlopen(yrUrls[k])
            ypage = BeautifulSoup(response)
            sels = ypage.find_all('select')
            for sel in sels:
                if 'name' in sel.attrs and sel['name'] == 'tournaments':
                    opts = sel.find_all('option')
                    for opt in opts:
                        if not opt['value']:
                            continue
                        print 'tourn', opt['value']
                        '''
                        response = urllib.urlopen(opt['value'])
                        tpage = BeautifulSoup(response)
                        for rnd in (1,2,3,4):
                            rdiv = tpage.find(id='round-%i-%s'%(rnd, self.activeKey))
                            if rdiv:
                                self.parse_round(rdiv)
                        '''

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

    def get_player_info(self):
        retDict = {}
        for k in self.playerMd:
            self.activeKey = k
            retDict[k] = {}
            #response = urllib.urlopen(self.playerMd[k]['playerLink'])
            pname = self.playerMd[k]['playerLink'].split("/")[-1]
            page = BeautifulSoup(readHtmlFile("data/%s"%(pname)))
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
            self.loop_through_tournaments(BASEURL+url)
        return retDict


pp = pageParser()