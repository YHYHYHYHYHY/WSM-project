import sys, math
from typing import Any, List, Dict
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt
from elasticsearch import Elasticsearch


host = 'localhost'
post = '9200'
es = Elasticsearch([{'host': host, 'port': post}])

# 分页表格控件，单选
class PageTableWidget(QtWidgets.QWidget):
    sinout_signal = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.init_data()
        self.init_ui()
        pass

    def init_data(self):
        self.table_full_data: List[Any] = []
        self.table_right_menus: Dict[str, str] = {}

        self.total_page_count: int = 0
        self.total_rows_count: int = 0
        self.current_page: int = 1
        self.single_page_rows: int = 10
        pass

    def init_ui(self):
        pre_page_btn = QtWidgets.QPushButton('上一页')
        pre_page_btn.clicked.connect(self.pre_page_btn_clicked)
        next_page_btn = QtWidgets.QPushButton('下一页')
        next_page_btn.clicked.connect(self.next_page_btn_clicked)

        tip_label_0 = QtWidgets.QLabel('第')
        self.witch_page_lineedit = QtWidgets.QLineEdit()
        self.int_validator = QtGui.QIntValidator()
        self.witch_page_lineedit.setValidator(self.int_validator)
        self.witch_page_lineedit.setMaximumWidth(20)
        tip_label_1 = QtWidgets.QLabel('页')
        go_page_btn = QtWidgets.QPushButton('前往')
        go_page_btn.clicked.connect(self.go_page_btn_clicked)
        layout_witch_page = QtWidgets.QHBoxLayout()
        layout_witch_page.addWidget(tip_label_0)
        layout_witch_page.addWidget(self.witch_page_lineedit)
        layout_witch_page.addWidget(tip_label_1)
        layout_witch_page.addWidget(go_page_btn)
        layout_witch_page.addStretch(1)

        self.total_page_count_label = QtWidgets.QLabel(f"共0页")
        self.total_rows_count_label = QtWidgets.QLabel(f"共找到0个结果")
        self.current_page_label = QtWidgets.QLabel(f"当前第0页")
        layout_pagestatus = QtWidgets.QHBoxLayout()
        layout_pagestatus.addWidget(self.total_page_count_label)
        layout_pagestatus.addWidget(self.total_rows_count_label)
        layout_pagestatus.addWidget(self.current_page_label)

        layout_top = QtWidgets.QHBoxLayout()
        layout_top.addWidget(pre_page_btn)
        layout_top.addWidget(next_page_btn)
        layout_top.addLayout(layout_witch_page)
        layout_top.addLayout(layout_pagestatus)
        layout_top.addStretch(1)

        self.target_table = QtWidgets.QTableWidget()
        self.target_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.target_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.target_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.target_table.customContextMenuRequested.connect(self.target_table_rightclicked_menu)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(layout_top)
        layout.addWidget(self.target_table)
        self.setLayout(layout)
        pass

    def set_table_init_data(self, data: Dict[str, Any]):
        headers: List[str] = data['headers']
        self.table_right_menus = data['table_right_menus']

        self.target_table.setColumnCount(len(headers))
        self.target_table.setHorizontalHeaderLabels(headers)
        pass

    def set_table_full_data(self, data: Dict[str, str]):
        self.table_full_data = data
        self.total_rows_count = len(data)
        self.total_page_count = math.ceil(self.total_rows_count / self.single_page_rows)
        self.current_page = 1

        self.int_validator.setRange(1, self.total_page_count)

        self.total_page_count_label.setText(f"共{self.total_page_count}页")
        self.total_rows_count_label.setText(f"共找到{self.total_rows_count}个结果")
        self.caculate_current_show_data()
        pass

    def setting_current_pagestatus_label(self):
        self.current_page_label.setText(f"当前第{self.current_page}页")
        pass

    def caculate_current_show_data(self):
        start_dot = (self.current_page - 1) * self.single_page_rows
        end_dot = start_dot + self.single_page_rows
        current_data = self.table_full_data[start_dot:end_dot]
        self.fill_table_content(current_data)
        self.setting_current_pagestatus_label()
        pass

    def fill_table_content(self, data: List[Any]):
        self.target_table.clearContents()
        self.target_table.setRowCount(len(data))
        for r_i, r_v in enumerate(data):
            id = r_v[0]
            body = {
                "query": {
                    "term": {
                        '_id': int(id)
                    }
                }
            }
            text = es.search(index="realnewslike_text", body=body)['hits']['hits'][0]['_source']['text']
            text = text[:80] + '...'

            cell_id = QtWidgets.QTableWidgetItem(id)
            cell_text = QtWidgets.QTableWidgetItem(text)
            self.target_table.setItem(r_i, 0, cell_id)
            self.target_table.setItem(r_i, 1, cell_text)

            pass
        self.target_table.resizeColumnsToContents()
        pass

    def go_page_btn_clicked(self):
        input_page = self.witch_page_lineedit.text()
        input_page = input_page.strip()
        if not input_page:
            QtWidgets.QMessageBox.information(
                self,
                '提示',
                '请输入要跳转的页码',
                QtWidgets.QMessageBox.Yes
            )
            return
        input_page = int(input_page)
        if input_page < 0 or input_page > self.total_page_count:
            QtWidgets.QMessageBox.information(
                self,
                '提示',
                '输入的页码超出范围',
                QtWidgets.QMessageBox.Yes
            )
            return
        self.current_page = input_page
        self.caculate_current_show_data()
        pass

    def pre_page_btn_clicked(self):
        if self.current_page <= 1:
            QtWidgets.QMessageBox.information(
                self,
                '提示',
                '已经是首页',
                QtWidgets.QMessageBox.Yes
            )
            return
        self.current_page -= 1
        self.caculate_current_show_data()
        pass

    def next_page_btn_clicked(self):
        if self.current_page >= self.total_page_count:
            QtWidgets.QMessageBox.information(
                self,
                '提示',
                '已经是最后一页',
                QtWidgets.QMessageBox.Yes
            )
            return
        self.current_page += 1
        self.caculate_current_show_data()
        pass

    def target_table_rightclicked_menu(self, pos):
        selectedItems = self.target_table.selectedItems()
        if len(selectedItems) <= 0:
            QtWidgets.QMessageBox.information(
                self,
                '提示',
                '请选择要操作的行',
                QtWidgets.QMessageBox.Yes
            )
            return
        if not self.table_right_menus:
            QtWidgets.QMessageBox.information(
                self,
                '提示',
                '没有右键菜单',
                QtWidgets.QMessageBox.Yes
            )
            return

        menu = QtWidgets.QMenu()
        menu_item_list = []
        for item in self.table_right_menus.keys():
            temp_item = menu.addAction(item)
            menu_item_list.append(temp_item)
            pass
        current_action = menu.exec_(self.target_table.mapToGlobal(pos))
        for item in menu_item_list:
            if item == current_action:
                # 发出信号
                action_name = item.text()
                pre_res_map = {}
                pre_res_map['action_name'] = action_name
                pre_res_map['action_target'] = self.table_right_menus[action_name]
                action_res_data = [i.text() for i in selectedItems]
                pre_res_map['action_data'] = action_res_data
                self.sinout_signal.emit(pre_res_map)
                break
            pass
        pass

    pass
class Example_widget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        pass
    def init_ui(self):
        self.setWindowTitle('表格显示示例')
        self.table = PageTableWidget()
        self.table.sinout_signal.connect(self.table_signal_recive)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)
        pass
    def setting_data(self,data1,data2):
        self.table.set_table_init_data(data1)
        self.table.set_table_full_data(data2)
        pass
    def table_signal_recive(self,data:Dict[str,Any]):
        print(data)
        pass

