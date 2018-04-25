import sys, os
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(sys.executable), 'pythonextensions/site-packages')))
pl_path = os.path.normpath(os.path.join(os.path.dirname(sys.executable), 'qtplugins/platforms'))
os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', pl_path)
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


class DropLineEdit(QLineEdit):
    def __init__(self, validator=None, placeholder=None):
        super(DropLineEdit, self).__init__()
        self.valid = validator
        if placeholder:
            self.setPlaceholderText(str(placeholder))
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            if len(event.mimeData().urls()) == 1:
                dir = event.mimeData().urls()[0].toLocalFile()

                if self.valid:
                    if self.valid(dir):
                        self.setText(dir)
                else:
                    self.setText(dir)
            else:
                event.ignore()
        else:
            event.ignore()


class GeneratorUi(QMainWindow):
    def __init__(self):
        super(GeneratorUi, self).__init__()
        self.centralwidget = QWidget(self)
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.gridLayout = QGridLayout()
        self.label = QLabel(self.centralwidget)
        self.label.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.reference_le = DropLineEdit(self.is_nuke_script, "Nuke Reference Script")
        self.label.setText("NK")
        self.gridLayout.addWidget(self.reference_le, 0, 1, 1, 1)
        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.mov_le = DropLineEdit(self.check_is_folder, "Premaster MOVs dir")
        self.label_2.setText("MOV")
        self.gridLayout.addWidget(self.mov_le, 1, 1, 1, 1)
        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.dpx_le = DropLineEdit(self.check_is_folder, "Source DPX Sequences Dir")
        self.label_3.setText("DPX")
        self.gridLayout.addWidget(self.dpx_le, 2, 1, 1, 1)
        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)
        self.out_le = DropLineEdit(self.check_is_folder, "Output Dir")
        self.label_4.setText("OUT")
        self.gridLayout.addWidget(self.out_le, 3, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.generate_btn = QPushButton(self.centralwidget)
        self.verticalLayout.addWidget(self.generate_btn)
        self.output_tb = QTextBrowser(self.centralwidget)
        self.verticalLayout.addWidget(self.output_tb)
        self.setCentralWidget(self.centralwidget)
        self.resize(700, 400)
        # sys.stdout = self.stdoutProxy(self.output)

        self.generate_btn.setText('Generate Scripts')
        self.generate_btn.clicked.connect(self.generate)
        self.process = QProcess()

    def output(self, *args):
        text = ' '.join([str(x) for x in args]).strip()
        self.output_tb.append(text)

    def check_is_folder(self, path):
        if not os.path.isdir(path):
            print('Path {} is not folder'.format(path))
            return False
        return True

    def is_nuke_script(self, path):
        if not os.path.isfile(path):
            print('Path {} is not file')
            return False
        if not os.path.splitext(path)[-1] == '.nk':
            print('Path {} is not nuke script')
            return False
        return True

    def generate(self):
        refscript = self.reference_le.text()
        movdir = self.mov_le.text()
        dpxdir = self.dpx_le.text()
        outdir = self.out_le.text()
        if not refscript:
            self.output('Reference Script not set')
            return
        if not os.path.exists(refscript):
            self.output('Reference Script not exists')
            return
        if not os.path.isdir(movdir):
            self.output('MOV Dir not exists')
            return
        if not os.path.isdir(dpxdir):
            self.output('DPX Dir not exists')
            return
        if not outdir:
            self.output('Output dir not set')
            return
        mov_files = [x for x in os.listdir(movdir) if os.path.splitext(x)[-1] == '.mov']
        dpx_shots = os.listdir(dpxdir)
        text = '''Reference Scripts: {}
Mov Files: {}
DPX Shots: {}
Output Path: {}'''.format(refscript, len(mov_files), len(dpx_shots), outdir)
        if QMessageBox.question(self, 'Generate Scripts', text) == QMessageBox.Yes:
            cmd = '{} {} {} {} {} {}'.format(
                sys.executable,
                os.path.join(os.path.dirname(__file__), 'generator.py'),
                refscript, movdir, dpxdir, outdir
            )
            self.generate_btn.setEnabled(False)
            self.process.setProcessChannelMode(QProcess.MergedChannels)
            self.process.readyRead.connect(self.process_output)
            self.process.finished.connect(self.complete)
            self.process.start(cmd)
        else:
            self.output('CANCEL GENERATION')

    def process_output(self):
        output = self.process.readAll()
        if not isinstance(output, str):
            if sys.version_info[0] < 3:
                output = str(output)
            else:
                output = str(output, 'utf-8')
        output = str(output).strip()
        if output:
            self.console_message(output)

    def complete(self):
        self.generate_btn.setEnabled(True)

    def console_message(self, msg):
        self.output_tb.insertPlainText('%s\n' % msg)
        self.output_tb.moveCursor(QTextCursor.End)


if __name__ == '__main__':
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    w = GeneratorUi()
    w.show()

    app.exec_()