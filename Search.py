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

# ----------- Prepare ---------------
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


# ----------- Ranked Search ---------------

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

    for term in terms:
        if term not in dictionary:
            continue
        posting_list = posting(term)
        freq_list = freqency(term)
        n = len(posting_list)
        idf = math.log10(total_num / n)
        for i in range(n):
            id = posting_list[i]

            freq = freq_list[i]
            tf = 1 + math.log10(freq)
            if id in score:
                score[id] += tf * idf
            else:
                score[id] = tf * idf


    sorted_score = sorted(zip(score.values(), score.keys()), reverse=True)
    sorted_id = [id for _, id in sorted_score]
    return sorted_id

# ----------- Boolean Search ---------------
def search(query):


    result = process_query(query, dictionary, post_file, indexed_docIDs)


    return result

def process_query(query, dictionary, post_file, indexed_docIDs):
    stemmer = nltk.stem.porter.PorterStemmer()
    query = query.replace('(', '( ')
    query = query.replace(')', ' )')
    query = query.split(' ')

    results_stack = []
    postfix_queue = collections.deque(shunting_yard(query))

    while postfix_queue:
        token = postfix_queue.popleft()
        result = []
        if (token != 'AND' and token != 'OR' and token != 'NOT'):
            token = stemmer.stem(token)
            if (token in dictionary):
                result = posting(token)

        elif (token == 'AND'):
            right_operand = results_stack.pop()
            left_operand = results_stack.pop()
            result = boolean_AND(left_operand, right_operand)

        elif (token == 'OR'):
            right_operand = results_stack.pop()
            left_operand = results_stack.pop()
            result = boolean_OR(left_operand, right_operand)

        elif (token == 'NOT'):
            right_operand = results_stack.pop()
            result = boolean_NOT(right_operand, indexed_docIDs)

        results_stack.append(result)

    if len(results_stack) != 1:
        print("ERROR: results_stack. Please check valid query")

    return results_stack.pop()


def shunting_yard(infix_tokens):
    precedence = {}
    precedence['NOT'] = 3
    precedence['AND'] = 2
    precedence['OR'] = 1
    precedence['('] = 0
    precedence[')'] = 0

    output = []
    operator_stack = []

    for token in infix_tokens:

        if (token == '('):
            operator_stack.append(token)

        elif (token == ')'):
            operator = operator_stack.pop()
            while operator != '(':
                output.append(operator)
                operator = operator_stack.pop()

        elif (token in precedence):
            if (operator_stack):
                current_operator = operator_stack[-1]
                while (operator_stack and precedence[current_operator] > precedence[token]):
                    output.append(operator_stack.pop())
                    if (operator_stack):
                        current_operator = operator_stack[-1]

            operator_stack.append(token)

        else:
            output.append(token.lower())

    while (operator_stack):
        output.append(operator_stack.pop())
    return output


def boolean_NOT(right_operand, indexed_docIDs):
    if (not right_operand):
        return indexed_docIDs

    result = []
    r_index = 0
    for item in indexed_docIDs:
        if (item != right_operand[r_index]):
            result.append(item)
        elif (r_index + 1 < len(right_operand)):
            r_index += 1
    return result


def boolean_OR(left_operand, right_operand):
    result = []
    l_index = 0
    r_index = 0

    while (l_index < len(left_operand) or r_index < len(right_operand)):
        if (l_index < len(left_operand) and r_index < len(right_operand)):
            l_item = left_operand[l_index]
            r_item = right_operand[r_index]

            if (l_item == r_item):
                result.append(l_item)
                l_index += 1
                r_index += 1

            elif (l_item > r_item):
                result.append(r_item)
                r_index += 1

            else:
                result.append(l_item)
                l_index += 1

        elif (l_index >= len(left_operand)):
            r_item = right_operand[r_index]
            result.append(r_item)
            r_index += 1

        else:
            l_item = left_operand[l_index]
            result.append(l_item)
            l_index += 1

    return result


def boolean_AND(left_operand, right_operand):
    result = []
    l_index = 0
    r_index = 0
    l_skip = int(math.sqrt(len(left_operand)))
    r_skip = int(math.sqrt(len(right_operand)))

    while (l_index < len(left_operand) and r_index < len(right_operand)):
        l_item = left_operand[l_index]
        r_item = right_operand[r_index]

        if (l_item == r_item):
            result.append(l_item)
            l_index += 1
            r_index += 1

        elif (l_item > r_item):
            if (r_index + r_skip < len(right_operand)) and right_operand[r_index + r_skip] <= l_item:
                r_index += r_skip
            else:
                r_index += 1

        else:
            if (l_index + l_skip < len(left_operand)) and left_operand[l_index + l_skip] <= r_item:
                l_index += l_skip
            else:
                l_index += 1

    return result


def boolean_search(query):

    return search(query)

if __name__ == "__main__":
    print(boolean_search('Trump AND Obama'))
