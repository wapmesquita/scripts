import json
import sys

if __name__ == "__main__":
    print sys.argv
    jsonfile = file(sys.argv[1], "r")
    data = json.loads(jsonfile.read())

    labels = {}
    lists = {}
    csvlist = [['Lista', 'Atividade', 'Descricao', 'Url']]

    for i in data['lists']:
        lists[i['id']] = i

    for c in data['cards']:
        csvlist.append([lists[c['idList']]['name'], c['name'], c['desc'], c['shortUrl']])

    for row in csvlist:
        text = ''
        for col in row:
            text=text+'"'+col+'";'
        print text
