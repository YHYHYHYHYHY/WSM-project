import nltk
import json
import math
import sys
import getopt
import codecs
import struct
import io
import collections
import timeit
from elasticsearch import Elasticsearch


host = 'localhost'
post = '9200'
es = Elasticsearch([{'host': host, 'port': post}])
porter = nltk.PorterStemmer()

total_num = 13978838

BYTE_SIZE = 4

root = 'full_env/'
dict_file = codecs.open(root+'dictionary', encoding='utf-8')
post_file = io.open(root+'postingfile', 'rb')
freq_file = io.open(root+'frequencyfile', 'rb')

def load_dictionary(dict_file):
    dictionary = {}                 # dictionary map loaded
    indexed_docIDs = []             # list of all docIDs indexed
    docIDs_processed = False        # if indexed_docIDs is processed

    # load each term along with its df and postings file pointer to dictionary
    for entry in dict_file.read().split('\n'):
        # if entry is not empty (last line in dictionary file is empty)
        if (entry):
            # if first line of dictionary, process list of docIDs indexed
            if (not docIDs_processed):
                indexed_docIDs = [int(docID) for docID in entry[20:-1].split(',')]
                docIDs_processed = True
            # else if dictionary terms and their attributes
            else:
                token = entry.split(" ")
                term = token[0]
                df = int(token[1])
                offset = int(token[2])
                dictionary[term] = (df, offset)

    return (dictionary, indexed_docIDs)

loaded_dict = load_dictionary(dict_file)
dictionary = loaded_dict[0]     # dictionary map
indexed_docIDs = loaded_dict[1] # list of all docIDs indexed in sorted order

def load_list(file, length, offset):
    file.seek(offset)
    return_list = []
    for i in range(length):
        f = file.read(BYTE_SIZE)
        item = struct.unpack('I', f)[0]
        return_list.append(item)
    return return_list

def posting(term):
    if term not in dictionary:
        pass
    df = dictionary[term][0]
    offset = dictionary[term][1]
    posting_list = load_list(post_file, df, offset)
    return posting_list

def freqency(term):
    if term not in dictionary:
        pass
    df = dictionary[term][0]
    offset = dictionary[term][1]
    freq_list = load_list(freq_file, df, offset)
    return freq_list

def rank(query):
    terms = nltk.word_tokenize(query)
    terms = [porter.stem(t) for t in terms]
    score = {}
    text_dic = {}

    for term in terms:
        if term not in dictionary:
            continue
        posting_list = posting(term)
        freq_list = freqency(term)
        n = len(posting_list)
        idf = math.log10(total_num / n)
        for i in range(n):
            id = posting_list[i]

            body = {
                "query": {
                    "term": {
                        '_id': id
                    }
                }
            }
            '''
            text = es.search(index="realnewslike_text", body=body)['hits']['hits'][0]['_source']['text']
            if id not in text_dic:
                text_dic[id] = text
            '''
            freq = freq_list[i]
            tf = 1 + math.log10(freq)
            if id in score:
                score[id] += tf * idf
            else:
                score[id] = tf * idf


    sorted_score = sorted(zip(score.values(), score.keys()), reverse=True)
    sorted_id = [id for _, id in sorted_score]
    return sorted_id


#print(len(posting('journey')))
#print(rank('journey water'))