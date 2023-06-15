from mainpage import Ui_SJTU  # 导入 uiDemo4.py 中的 Ui_MainWindow 界面类
from resultpage2 import ResultPage2
from resultpage1 import ResultPage1
from QA_sum_page import QA_sum_page
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from RankedSearch import rank
from QA_S.summarize_QA import summarize, QA
from Table import PageTableWidget
from FullText_page import FullTextPage
from elasticsearch import Elasticsearch
import nltk
from nltk.tokenize.treebank import TreebankWordDetokenizer

host = 'localhost'
post = '9200'
es = Elasticsearch([{'host': host, 'port': post}])

class MainWindow(QMainWindow, Ui_SJTU):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.show()
        self.page1 = PageWindow1()
        self.page2 = PageWindow()
        self.pushButton.clicked.connect(self.page1.show)
        self.pushButton_2.clicked.connect(self.page2.show)

    def get_query(self):
        query = self.textEdit.toPlainText()
        self.page1.textEdit.setText(query)
        res = rank(query)
        self.page1.prepare(res)


    def get_bool(self):
        query = self.textEdit.toPlainText()
        self.page2.textEdit.setText(query)
        res = rank(query) # 这里要调Boolean search的接口
        self.page2.prepare(res)




class PageWindow(QMainWindow, ResultPage2): # Boolean Search Page
    def __init__(self, parent=None):
        super(PageWindow, self).__init__(parent)
        self.setupUi(self)
        self.table = PageTableWidget()
        self.verticalLayout.addWidget(self.table)
        self.FullTextWindow = PageWindow3()


    def search(self):
        query = self.textEdit.toPlainText()
        res = rank(query) # 这里要调Boolean search的接口
        self.prepare(res)

    def prepare(self, ranked_result): # 根据Boolean search返回的数据结构重写prepare方法
        pre_data = {}
        pre_data['headers'] = ['DocID', 'News']
        pre_data['table_right_menus'] = {
            'Full Text': 'target_11',
        }
        pre_body_data = []
        for id in ranked_result:
            pre_body_data.append(str(id))
        self.table.set_table_init_data(pre_data)
        self.table.set_table_full_data(pre_body_data)

    def FullText(self):
        if len(self.table.target_table.selectedItems()) <= 0:
            QtWidgets.QMessageBox.information(
                self,
                'Warning!',
                'Please select the row to operate on',
                QtWidgets.QMessageBox.Yes
            )
            self.FullTextWindow.close()
            return
        id = self.table.target_table.selectedItems()[0].text()
        id = int(id)
        body = {
            "query": {
                "term": {
                    '_id': int(id)
                }
            }
        }
        text = es.search(index="realnewslike_text", body=body)['hits']['hits'][0]['_source']['text']

        self.FullTextWindow.textBrowser.setText(text)
        self.FullTextWindow.show()



class PageWindow1(QMainWindow, ResultPage1): # Ranked Search Page
    def __init__(self, parent=None):
        super(PageWindow1, self).__init__(parent)
        self.setupUi(self)
        self.QA_page = PageWindow2()
        self.sum_page = PageWindow2()
        self.table = PageTableWidget()
        self.verticalLayout.addWidget(self.table)
        self.FullTextWindow = PageWindow3()
        # self.pushButton_4.clicked.connect(self.FullTextWindow.show)


    def getQA(self):
        question = self.textEdit.toPlainText()
        res = rank(question)[:10]
        for score, id in res:
            body = {
                "query": {
                    "term": {
                        '_id': int(id)
                    }
                }
            }
            text = es.search(index="realnewslike_text", body=body)['hits']['hits'][0]['_source']['text']
            text = gettopsentences(20, text)
            answer = QA(question, text)
            if answer != '<s>':
                break
        self.QA_page.textBrowser.setText(answer)
        self.QA_page.setWindowTitle('Q&A')
        self.QA_page.show()
    def getsum(self):
        query = self.textEdit.toPlainText()
        res = rank(query)[:10]
        context = ''
        for score, id in res:
            body = {
                "query": {
                    "term": {
                        '_id': int(id)
                    }
                }
            }
            text = es.search(index="realnewslike_text", body=body)['hits']['hits'][0]['_source']['text']
            text = gettopsentences(10, text)
            context += text
        if len(nltk.word_tokenize(context)) >= 3700:
            l = len(nltk.word_tokenize(context))
            context = TreebankWordDetokenizer().detokenize(nltk.word_tokenize(context)[:3700])
        answer = summarize(context)
        self.sum_page.textBrowser.setText(answer['generated_summaries'][0])
        self.sum_page.setWindowTitle("Summarize")
        self.sum_page.show()
    def search(self):
        query = self.textEdit.toPlainText()
        res = rank(query)
        self.prepare(res)
    def prepare(self, ranked_result):
        pre_data = {}
        pre_data['headers'] = ['DocID', 'News']
        pre_data['table_right_menus'] = {
            'Full Text': 'target_11',
        }
        pre_body_data = []
        for id in ranked_result:
            pre_body_data.append(str(id))
        self.table.set_table_init_data(pre_data)
        self.table.set_table_full_data(pre_body_data)
    def FullText(self):
        if len(self.table.target_table.selectedItems()) <= 0:
            QtWidgets.QMessageBox.information(
                self,
                'Warning!',
                'Please select the row to operate on',
                QtWidgets.QMessageBox.Yes
            )
            self.FullTextWindow.close()
            return
        id = self.table.target_table.selectedItems()[0].text()
        id = int(id)
        body = {
            "query": {
                "term": {
                    '_id': int(id)
                }
            }
        }
        text = es.search(index="realnewslike_text", body=body)['hits']['hits'][0]['_source']['text']

        self.FullTextWindow.textBrowser.setText(text)
        self.FullTextWindow.show()


class PageWindow2(QMainWindow, QA_sum_page): # QA & Summarize Page
    def __init__(self, parent=None):
        super(PageWindow2, self).__init__(parent)
        self.setupUi(self)
        self.pushButton.clicked.connect(self.clickButtonCloseWindow)

    def clickButtonCloseWindow(self):
        self.close()

class PageWindow3(QMainWindow, FullTextPage): # Full Text Page
    def __init__(self, parent=None):
        super(PageWindow3, self).__init__(parent)
        self.setupUi(self)
        self.pushButton.clicked.connect(self.clickButtonCloseWindow)

    def clickButtonCloseWindow(self):
        self.close()

def gettopsentences(k, text): # Get top k sentences
    tokens = nltk.word_tokenize(text)
    sentence = 0
    end_list = ['.', '?', '!']
    for i in range(len(tokens)):
        if tokens[i] in end_list:
            sentence += 1
            if sentence >= k:
                return TreebankWordDetokenizer().detokenize(tokens[:i])
    return text

if __name__ == '__main__':
    app = QApplication(sys.argv)
    myWin = MainWindow()

    sys.exit(app.exec_())
