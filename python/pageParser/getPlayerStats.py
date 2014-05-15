from bs4 import BeautifulSoup
import urllib 

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

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

pp = pageParser()