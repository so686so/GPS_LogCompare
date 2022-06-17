# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- #
TITLE       = 'GPS Log Compare Program for GNET System'
VERSION     = '1.0.4'
AUTHOR      = 'So Byung Jun'
UPDATE      = '2022-6-16'
GIT_LINK    = 'https://github.com/so686so/GPS_LogCompare.git'
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- #

# Windows .exe Command : 'pyinstaller --icon=./ProgramIcon.ico -F CompareProgram.py' (need 'CompareProgram.spec')
# exe 파일 패키징을 위해 코드 한곳에 통합

"""
    [INV]   - 로그 내 특정 값 자체가 유효하지 않음
    [DIF]   - 로그 내 특정 값이 다름
    [MIS]   - 누락
    [O]     - 모두 매칭됨
"""

# Import Packages and Modules
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
# Standard Library
# -------------------------------------------------------------------
import  json
import  os
import  sys
import  time
from    shutil                  import copyfile
from    math                    import fabs
from    datetime                import datetime

# Installed Library
# -------------------------------------------------------------------
from    chardet                 import detect      
from    iteration_utilities     import unique_everseen, duplicates

USE_PYQT5 = False

# For GUI ( Ver. PyQt 6.2.2 )
# -------------------------------------------------------------------
if USE_PYQT5 is True:
    from    PyQt5.QtCore            import *
    from    PyQt5.QtGui             import *
    from    PyQt5.QtWidgets         import *
else:
    from    PyQt6.QtCore            import *
    from    PyQt6.QtGui             import *
    from    PyQt6.QtWidgets         import *
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-


# Const Define
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
# 중복값 매칭 시 우선순위 조절 위한 값
FIRST = '최초값 우선'
LAST  = '마지막값 우선'

# 텍스트 파일 불러올 때 유효한 인코딩 값
VALID_ENCODING_FORMAT   = [ 'utf-8', 'ascii', 'ecu-kr', 'cp949' ]

# 기타 Const
ENCODING_PREPIX         = 'ENC_'
CUR_PATH                = os.path.dirname('./')

# 인코딩 컨버트할 때 변환할 포맷
CONVERT_ENCODING        = 'utf-8'

# 모니터 해상도 못 불러왔을 때 기본 UI 창 크기
WINDOW_WIDTH            = 800
WINDOW_HEIGHT           = 650

# 로그 텍스트 파일 형식에서 필요한 대괄호 [] 갯수
NEED_BRACKET_COUNT      = 2

# 각 로그 체크값을 문자열 그대로 할지, 숫자로 변환해 할지 타입 지정용 변수
TYPE_STR                = 0
TYPE_FLOAT              = 1
TYPE_TABLE              = ['문자열 그대로', '숫자로 변환']

# KEYLOG DLG Setting
DLG_HEADER_LEN          = 2
DLG_IDX_NAME            = 0
DLG_IDX_TYPE            = 1


# Var Define : UI 시작할 때 초기 세팅값이고, UI를 통해 변경 가능
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
DEBUG_MODE          = True

# 중복값 매칭 우선순위
DUPLICATE_PRIORITY  = FIRST

# 기본 파일 경로들
VIEWER_FILE         = './viewer.txt'
SERVER_FILE         = './server.txt'
RESULT_DIR          = CUR_PATH
RESULT_FILE         = 'IOT_GPS_로그값_비교_결과.txt'

# 매치 체크할 때 검사할 키값 목록
CHECK_DETAIL_LIST   = [ TYPE_STR, TYPE_FLOAT, TYPE_FLOAT, TYPE_FLOAT, TYPE_FLOAT,  TYPE_STR ]
MATCH_CHECK_LIST    = [ 'time',   'speed',    'bearing',  'latitude', 'longitude', 'status' ]
UNMATCH_COUNT_LIST  = [ 0 for _ in MATCH_CHECK_LIST ]

# DateTime StringFormat
DATETIME_FORMAT     = "%Y-%m-%d %H:%M:%S"


# Common Use Class : Signal
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
class ProgressSignal(QObject):
    signal              = pyqtSignal(int)
    addProgressCount    = 10
    curProgress         = 0
    isSetStage          = False

    # 실제 시그널 보내는 함수
    def sendProgress(self) -> None:
        if self.isSetStage:
            self.signal.emit(self.curProgress)

    # 해당 함수가 실행되어야지 스테이지별 진행 송신 가능
    def initStage(self, stage:int) -> None:
        self.curProgress = 0
        self.isSetStage  = True

        if stage < 1:
            self.addProgressCount = 10
        elif stage > 100:
            self.addProgressCount = 1
        else:
            self.addProgressCount = (int)(100 / stage)

    # 한 스테이지 클리어, initStage에서 정해둔 값만큼 progress 증가
    def sendPerStageClear(self):
        if self.isSetStage:
            self.curProgress += self.addProgressCount
            self.sendProgress()

    # 진행 실패, 0으로 초기화
    def sendStageFail(self):
        if self.isSetStage:
            self.curProgress = 0
            self.sendProgress()
        
    def sendStageFinish(self):
        self.curProgress = 100
        self.sendProgress()
        self.isSetStage  = False


# FileChecker : FileCheck 및 인코딩 체크, 인코딩 변환 및 Json Read
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
class FileChecker:
    def __init__( self, logKeyList=MATCH_CHECK_LIST, convert_encoding=CONVERT_ENCODING ):
        self.__targetFile       = r""
        self.__targetFormat     = None

        self.__convertFile      = r""
        self.__convertFormat    = convert_encoding
        
        self.__isDoneCorrect    = False
        self.__newCorrectJson   = False

        self.__jsonObject       = None
        self._checkLogKeyList   = logKeyList

    # getter & setter
    # -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    @property
    def targetFile(self):
        return self.__targetFile

    @targetFile.setter
    def targetFile(self, fileName:str):
        if os.path.isfile(fileName) is False and fileName:
            print(f"[!] \'{fileName}\'는 유효한 파일이 아닙니다.")
            return
        self.__targetFile = fileName

    @property
    def targetFormat(self):
        return self.__targetFormat

    @targetFormat.setter
    def targetFormat(self, encodingFormat:str):
        if encodingFormat not in VALID_ENCODING_FORMAT and encodingFormat:
            print(f'[!] {encodingFormat} 형식은 유효한 인코딩 형식이 아닙니다.')
            self.__targetFormat = None
            return
        self.__targetFormat = encodingFormat

    @property
    def convertFile(self):
        return self.__convertFile

    @convertFile.setter
    def convertFile(self, convertName):
        if os.path.isfile(convertName) is False and convertName:
            print(f"[!] \'{convertName}\'는 유효한 파일이 아닙니다.")
            return
        if ENCODING_PREPIX in convertName:
            self.__convertFile = convertName
        else:
            print(f'[!] 정상적이지 않은 방법으로 Convert 파일이 입력되었습니다. 파일 세팅 취소.')
            self.__convertFile = r""
            return

    @property
    def jsonObject(self):
        DATA_INDEX = 0
        return self.__jsonObject[DATA_INDEX]

    @jsonObject.setter
    def jsonObject(self, convertName):
        if self.newCorrectJson is True:
            self.__jsonObject   = convertName
            self.newCorrectJson = False
        else:
            print("[!] 유효하지 않은 방식으로 Json 파일이 입력되었습니다.")
            self.__jsonObject = None

    @property
    def isDoneCorrect(self):
        return self.__isDoneCorrect

    @isDoneCorrect.setter
    def isDoneCorrect(self, bVal:bool):
        self.__isDoneCorrect = bVal

    @property
    def newCorrectJson(self):
        return self.__newCorrectJson

    @newCorrectJson.setter
    def newCorrectJson(self, bVal:bool):
        self.__newCorrectJson = bVal

    @property
    def convertFormat(self):
        return self.__convertFormat


    # Function
    # -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    # targetFile 의 인코딩 형식을 반환하는 함수
    def checkFileEncodingFormat(self) -> str:
        if not self.targetFile:
            print('[!] 유효성 체크를 할 파일이 존재하지 않습니다.')
            return None

        try:
        # CP949, EUC-KR, ASCII
            with open(self.targetFile, 'r') as rf:
                file_data = rf.readline()
            return detect(file_data.encode())['encoding']

        # UTF-8 cannot read by readline() func
        except Exception:
            return 'utf-8'


    # 새로운 파일을 targetFile 에 등록하는 함수
    def registerNewFile(self, fileName:str):
        # 기존값 백업
        prevFileName      = self.targetFile
        prevFileFormat    = self.targetFormat

        self.targetFile   = fileName
        self.targetFormat = self.checkFileEncodingFormat() 

        print()

        # setter 정상적으로 완료되고, 인코딩 포맷까지 정상적으로 읽어졌을 때
        if self.targetFile == fileName and self.targetFormat:
            # Reset Check Flags
            self.isDoneCorrect  = False
            self.newCorrectJson = False
            print(f'[v] 신규 체크파일 등록 - {fileName} ({self.targetFormat})')

        # 둘 중 하나라도 만족하지 못할 경우 롤백
        else:
            print(f'[!] 신규 체크 파일 \'{fileName}\' 등록이 실패했습니다. 이전값으로 돌아갑니다..')
            self.targetFile   = prevFileName
            self.targetFormat = prevFileFormat

        return self


    # targetFile 의 인코딩 포맷을 self.convertFormat 으로 변환하여 저장하는 함수
    def convertFileEncodingFormat(self):
        if not self.targetFile:
            print('[!] 등록된 파일이 유효하지 않습니다.')
            return False
        
        if not self.targetFormat:
            print("[!] 타겟 파일의 인코딩 형식을 불러올 수 없습니다. 파일을 UTF-8 로 저장하는 것을 권장합니다.")
            return False

        baseName = os.path.basename(self.targetFile)
        destFile = f'./{ENCODING_PREPIX}{baseName}'

        # 인코딩 포맷 동일하면 그냥 그대로 복사
        if self.targetFormat == self.convertFormat:
            copyfile(self.targetFile, destFile)

        elif self.targetFormat == 'ascii':
            blockSize = 256 * 256 * 16
            try:
                with open(self.targetFile, 'r', encoding='mbcs') as rf:
                    with open(destFile, 'w', encoding=self.convertFormat) as wf:
                        while True:
                            contents = rf.read(blockSize)
                            if not contents:
                                break
                            wf.write(contents)
            except Exception:
                print(f'[!] 파일 형식 변환에 실패했습니다. \'{self.targetFile}\' 파일을 UTF-8 형식으로 저장해주세요.')
                return False

        else:
            print(f'[!] \'{self.targetFile}\' 메모장 파일 형식을 ANSI 혹은 UTF-8로 다시 저장해 주세요.')
            return False

        self.convertFile = destFile

        print(f'[v] \'{self.targetFile}\' File Convert : \'{self.convertFile}\' ({self.targetFormat} -> {self.convertFormat})')
        return True


    def checkFileBrackets(self, srcLineList:list):
        startBracket    = 0
        endBracket      = 0
        startString     = ""
        endString       = ""

        # 파일 처음과 마지막 10줄을 읽어서 괄호쌍 찾고 갯수 파악하기
        for eachStr in srcLineList[:10]:
            startString += str(eachStr).strip()
        for eachStr in srcLineList[-10:]:
            endString   += str(eachStr).strip()

        for eachChar in startString:
            if eachChar == '[':
                startBracket += 1

        endString = endString[::-1]

        for eachChar in endString:
            if eachChar == ']':
                endBracket += 1

        if startBracket != NEED_BRACKET_COUNT or endBracket != NEED_BRACKET_COUNT:
            print("[#] 파일의 괄호가 주어진 형식에 맞지 않아 보정합니다")

            if startBracket != NEED_BRACKET_COUNT:
                addBracket = '[' * (NEED_BRACKET_COUNT - startBracket)
                srcLineList.insert(0, addBracket)

            if endBracket != NEED_BRACKET_COUNT:
                if endString[0] == ',':
                    srcLineList[-1] = str(srcLineList[-1]).rstrip().replace(',', '')
                addBracket = ']' * (NEED_BRACKET_COUNT - endBracket)
                srcLineList.append(addBracket)

            return srcLineList, True
        
        return srcLineList, False


    def checkJsonDelimiter(self, srcLineList:list):
        bChanged = False
        for idx, line in enumerate(srcLineList):
            sline = str(line).rstrip()
            for eachKey in self._checkLogKeyList[:-1]:
                if eachKey in sline and sline[-1] == "\"":
                    sline               += ",\n"
                    srcLineList[idx]    = sline
                    bChanged            = True
        if bChanged is True:
            print('[#] 파일의 Json 구분자가 명확하지 않아 보정합니다')
        return srcLineList, bChanged


    # JsonRead 를 하려 했는데, 파일의 괄호가 알맞게 작성되어있지 않는 경우에 자동 보정
    def correctionWorkForReadJson(self):
        if not self.convertFile:
            print('[!] 인코딩 형식 변환된 파일이 없습니다.')
            return False

        print(f'[#] Json read 를 위한 파일 보정 체크 : {self.convertFile}')

        bChanged = False
        lineList = ""
        with open(self.convertFile, 'r', encoding=self.convertFormat) as rf:
            lineList = rf.readlines()

        # 임시 보정
        lineList, tmpChanged = self.checkJsonDelimiter(lineList)
        bChanged |= tmpChanged

        lineList, tmpChanged = self.checkFileBrackets(lineList)
        bChanged |= tmpChanged

        if bChanged is True:
            print(f'[#] \'{self.targetFile}\' 이 Json read 에 적합하지 않아 보정을 시도합니다.')

            try:
                with open(self.convertFile, 'w', encoding=self.convertFormat) as wf:
                    for line in lineList:
                        wf.write(line)
                print('[v] 보정 완료.')
            except Exception:
                print("[!] 보정 실패.")
                return False
        else:
            print("[#] 보정이 필요없는 파일입니다.")

        self.isDoneCorrect = True
        return True


    def tryReadJsonFile(self):
        if self.isDoneCorrect is False:
            print('[!] 파일의 JsonRead 보정이 끝나지 않았습니다. 이게 나오면 안될텐데...')
            return False

        tmpJsonObject = None

        try:
            with open(self.convertFile, 'r', encoding=self.convertFormat) as f:
                tmpJsonObject = json.load(f)

            self.newCorrectJson = True
            self.jsonObject     = tmpJsonObject
            return True

        except Exception as e:
            print(f"[!] \'{self.targetFile}\' 의 Json Read 가 실패했습니다. 실패 위치 - {e}")
            return False


    def readJsonFile(self):
        if self.convertFileEncodingFormat() is False:
            return None

        if self.correctionWorkForReadJson() is False:
            return None

        if self.tryReadJsonFile() is False:
            return None

        return self.jsonObject


    def __del__(self):
        if os.path.isfile(self.convertFile) and DEBUG_MODE is False:
            os.remove(self.convertFile)


# CompareProgram : FileCheck로 로그파일을 불러와서 실제 비교하는 클래스
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
class CompareProgram:
    def __init__(self, pgSignal:ProgressSignal) -> None:
        self.__dateTimeFormat       = DATETIME_FORMAT
        self.__matchCheckKeyList    = MATCH_CHECK_LIST
        self.__keyDetailList        = CHECK_DETAIL_LIST
        self.__unmatchCountList     = [ 0 for _ in MATCH_CHECK_LIST ]
        self.__invalidVlaueCount    = 0
        self.__resultSaveDir        = RESULT_DIR
        self.__dupPriority          = DUPLICATE_PRIORITY

        self.progressSignal         = pgSignal

        self.__serverOriginLogList  = [] 
        self.__viewerOriginLogList  = []

        self.__serverDateTimeList   = []
        self.__viewerDateTimeList   = []

        self.__serverDupList        = []

        self.__tmpMatchingList      = []
        self.__allMatchingList      = []
        self.__missingList          = []

        self.__cmpServerLogDict     = []
        self.__cmpViewerLogDict     = []

    # getter & setter
    # -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    @property
    def dateTimeFormat(self):
        return self.__dateTimeFormat

    @dateTimeFormat.setter
    def dateTimeFormat(self, dtFormat:str):
        self.__dateTimeFormat = dtFormat


    @property
    def resultSaveDir(self):
        return self.__resultSaveDir

    @resultSaveDir.setter
    def resultSaveDir(self, resultDir:str):
        if os.path.isdir(resultDir) is True:
            self.__resultSaveDir = resultDir


    @property
    def dupPriority(self):
        return self.__dupPriority

    @dupPriority.setter
    def dupPriority(self, priority:str):
        if priority == FIRST or priority == LAST:
            self.__dupPriority = priority


    @property
    def matchCheckKeyList(self):
        return self.__matchCheckKeyList

    @matchCheckKeyList.setter
    def matchCheckKeyList(self, keyList:list):
        self.__matchCheckKeyList = keyList


    @property
    def keyDetailList(self):
        return self.__keyDetailList

    @keyDetailList.setter
    def keyDetailList(self, detailList:list):
        tList = []
        for eachType in detailList:
            if eachType not in [ TYPE_STR, TYPE_FLOAT ]:
                print('[!] 유효하지 않은 로그키값 타입이 있습니다 : 문자열 타입으로 자동 보정')
                tList.append(TYPE_STR)
            else:
                tList.append(eachType)
        self.__keyDetailList = tList


    @property
    def unmatchCountList(self):
        return self.__unmatchCountList

    @unmatchCountList.setter
    def unmatchCountList(self, countList:list):
        self.__unmatchCountList = countList


    @property
    def invalidVlaueCount(self):
        return self.__invalidVlaueCount

    @invalidVlaueCount.setter
    def invalidVlaueCount(self, nCount:int):
        self.__invalidVlaueCount = nCount


    @property
    def serverOriginLogList(self):
        return self.__serverOriginLogList

    @serverOriginLogList.setter
    def serverOriginLogList(self, logList:list):
        if not logList:
            print('[!] 서버 로그가 유효하지 않습니다.')
            return
        self.__serverOriginLogList = logList


    @property
    def viewerOriginLogList(self):
        return self.__viewerOriginLogList

    @viewerOriginLogList.setter
    def viewerOriginLogList(self, logList:list):
        if not logList:
            print('[!] 뷰어 로그가 유효하지 않습니다.')
            return
        self.__viewerOriginLogList = logList


    @property
    def serverDateTimeList(self):
        return self.__serverDateTimeList

    @serverDateTimeList.setter
    def serverDateTimeList(self, dtList:list):
        self.__serverDateTimeList = dtList


    @property
    def viewerDateTimeList(self):
        return self.__viewerDateTimeList

    @viewerDateTimeList.setter
    def viewerDateTimeList(self, dtList:list):
        self.__viewerDateTimeList = dtList


    @property
    def serverDupList(self):
        return self.__serverDupList

    @serverDupList.setter
    def serverDupList(self, dupList:list):
        self.__serverDupList = dupList


    @property
    def tmpMatchingList(self):
        return self.__tmpMatchingList

    @tmpMatchingList.setter
    def tmpMatchingList(self, tmpMatchList:list):
        self.__tmpMatchingList = tmpMatchList


    @property
    def allMatchingList(self):
        return self.__allMatchingList

    @allMatchingList.setter
    def allMatchingList(self, allMatchList:list):
        self.__allMatchingList = allMatchList


    @property
    def missingList(self):
        return self.__missingList

    @missingList.setter
    def missingList(self, mList:list):
        self.__missingList = mList


    @property
    def cmpServerLogDict(self):
        return self.__cmpServerLogDict

    @cmpServerLogDict.setter
    def cmpServerLogDict(self, cmpDict:dict):
        self.__cmpServerLogDict = cmpDict


    @property
    def cmpViewerLogDict(self):
        return self.__cmpViewerLogDict

    @cmpViewerLogDict.setter
    def cmpViewerLogDict(self, cmpDict:dict):
        self.__cmpViewerLogDict = cmpDict


    # Function
    # -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    def convertDateStringToDateTime(self, dateString:str):
        return datetime.strptime(dateString, self.dateTimeFormat)

    def convertDateTimeToDateString(self, dateTime):
        return datetime.strftime(dateTime, self.dateTimeFormat)

    def SendProgress(self, progress=0):
        if 0 <= progress <= 100:
            self.progressSignal.sendProgress(progress)
        elif progress < 0:
            self.progressSignal.sendProgress(0)
        elif progress > 100:
            self.progressSignal.sendProgress(100)

    def InitRunStage(self, stage=1):
        self.progressSignal.initStage(stage)

    def RunFail(self, log=''):
        print(log)
        self.progressSignal.sendStageFail()
        return False

    def RunSuccess(self):
        self.progressSignal.sendPerStageClear()

    def RunFinish(self):
        self.progressSignal.sendStageFinish()

    def setLogFiles(self, vFile=VIEWER_FILE, sFile=SERVER_FILE, logKeyList=MATCH_CHECK_LIST):
        self.InitRunStage(5)
        self.viewerOriginLogList.clear()
        self.serverOriginLogList.clear()

        vf = FileChecker(logKeyList)
        self.viewerOriginLogList = vf.registerNewFile(vFile).readJsonFile()

        sf = FileChecker(logKeyList)
        self.serverOriginLogList = sf.registerNewFile(sFile).readJsonFile()

        if not self.viewerOriginLogList:
            return self.RunFail("[!] 뷰어 로그 파일이 유효하지 않습니다.")
        self.RunSuccess()

        if not self.serverOriginLogList:
            return self.RunFail("[!] 서버 로그 파일이 유효하지 않습니다.")
        self.RunSuccess()

        print()
        print('--------------------------------------------------------------')
        print(f'[v] LogFile 세팅 완료 : \'{vFile}\' & \'{sFile}\'')
        print('--------------------------------------------------------------')

        if self.checkDateTimeFormatOK() is False:
            return self.RunFail()
        self.RunSuccess()

        if self.checkKeyNameOK() is False:
            return self.RunFail()
        self.RunSuccess()

        self.setDateTimeList()
        self.RunFinish()
        return True

    def checkDateTimeFormatOK(self):
        currentFile     = 'ViewerLog'
        currentLogTime  = ''
        try:
            for eachLog in self.viewerOriginLogList:
                currentLogTime = eachLog['time']
                _ = self.convertDateStringToDateTime(currentLogTime)    
            currentFile = 'ServerLog'        
            for eachLog in self.serverOriginLogList:
                currentLogTime = eachLog['time']
                _ = self.convertDateStringToDateTime(currentLogTime)
            return True
        except Exception:
            print()
            print('[!] 입력한 Time 형식이 유효하지 않습니다. 다시 입력해 주세요.')
            print(f'[i] 오류 파일 : {currentFile}')
            print(f'[i] 오류 Time 값: {currentLogTime}')
            print(f'[i] 설정 Time 형식 : {self.dateTimeFormat}')
            return False

    def checkKeyNameOK(self):
        errorPos = {}
        try:
            for eachDict in self.viewerOriginLogList:
                errorPos = eachDict
                for eachKey in self.matchCheckKeyList:
                    _ = eachDict[eachKey]
            return True
        except Exception:
            print()
            print('[!] 입력한 로그 체크값 중 실제 뷰어 파일에 없는 체크값이 있습니다. 다시 입력해 주세요.')
            print(f'[!] 에러 위치 : {errorPos["time"]}')
            return False

    # Not Use Yet
    def checkKeyTypeOK(self):
        errorPos = {}
        try:
            for eachDict in self.viewerOriginLogList:
                errorPos = eachDict
                for idx, eachKey in enumerate(self.matchCheckKeyList):
                    if self.keyDetailList[idx] == TYPE_STR:
                        _ = str(errorPos[eachKey])
                    else:
                        _ = float(errorPos[eachKey])
            return True
        except Exception:
            print()
            print('[!] 입력한 로그 체크값 중 지정한 문자열/실수 변환을 할 수 없는 값이 있습니다')
            print(f'[!] 에러 위치 : {errorPos["time"]}')
            return False

    def setDateTimeList(self):
        self.serverDateTimeList.clear()
        self.viewerDateTimeList.clear()

        self.serverDateTimeList = [ self.convertDateStringToDateTime(t['time']) for t in self.serverOriginLogList ]
        self.viewerDateTimeList = [ self.convertDateStringToDateTime(t['time']) for t in self.viewerOriginLogList ]


    def findDuplicateLogByServer(self):
        print()
        print('==============================================================')
        print('[*] 서버 로그 파일에서 중복 파일이 있는지 체크합니다.')
        print('==============================================================')
        print(f'[i] 총 서버 로그 갯수 : {len(self.serverOriginLogList)}')
        print('--------------------------------------------------------------')

        self.serverDupList = list(unique_everseen(duplicates(self.serverDateTimeList)))

        print('[v] 중복 확인 완료')
        print(f'[i] 총 중복 갯수 : {len(self.serverDupList)}')
        print('--------------------------------------------------------------')

        if self.serverDupList:
            for each in self.serverDupList:
                print(self.convertDateTimeToDateString(each))
            print('--------------------------------------------------------------')
        print()
        self.RunSuccess()


    def findMissingLogCompareServerAndViewer(self):
        print()
        print('==============================================================')
        print('[*] 뷰어 로그 파일과 비교하여 누락된 서버 로그 파일이 있는지 체크합니다.')
        print('==============================================================')
        print(f'[i] Viewer 로그 갯수 : {len(self.viewerOriginLogList)}')
        print(f'[i] Server 로그 갯수 : {len(self.serverOriginLogList)}')

        self.tmpMatchingList = list(set(self.viewerDateTimeList) & set(self.serverDateTimeList))
        self.missingList     = list(set(self.viewerDateTimeList) - set(self.serverDateTimeList))

        self.tmpMatchingList = [ self.convertDateTimeToDateString(t) for t in self.tmpMatchingList ]
        self.missingList     = [ self.convertDateTimeToDateString(t) for t in self.missingList ]

        self.tmpMatchingList.sort()
        self.missingList.sort()

        print('--------------------------------------------------------------')
        print(f'[v] 누락 파일 확인 완료')
        print('--------------------------------------------------------------')
        print(f'[*] time 값 매칭된 로그 갯수 : {len(self.tmpMatchingList)}')
        print(f'[*] 매칭 누락된 로그 갯수 : {len(self.missingList)}')
        print('--------------------------------------------------------------')
        self.RunSuccess()


    def makeCompareDictFromTmpMatchingList(self):
        print()
        print('==============================================================')
        print('[*] 매칭 및 부분 매칭을 체크하기 위한 데이터를 정제합니다. 해당 작업은 시간이 오래 걸릴 수 있습니다.')
        print('==============================================================')

        if not self.tmpMatchingList:
            return self.RunFail('[!] 누락 체크 후 임시 매칭된 데이터 자료가 없습니다. 로그 파일을 확인해주세요')

        print(f'[*] Make Viewer Compare Data From tempMatchLogList :: {datetime.strftime(datetime.now(), DATETIME_FORMAT)}')
        print(f'[*] Try to matching \'{len(self.tmpMatchingList)} X {len(self.viewerOriginLogList)}\' Log Data')
        start = time.time()

        progressPrcnt = 1
        progressMount = 0
        addMountVal   = len(self.tmpMatchingList) / 20

        tmpViewerDict = {}
        # Viewer
        for eachDateString in self.tmpMatchingList:
            
            progressMount += 1
            if progressMount >= addMountVal * progressPrcnt:
                print(f'  [>] Data Processing... {progressPrcnt*5:3}%')
                self.RunSuccess()
                progressPrcnt += 1

            for eachDict in self.viewerOriginLogList:
                if eachDateString == eachDict['time']:
                    if self.dupPriority == FIRST and tmpViewerDict.get(eachDateString):
                        continue
                    tmpViewerDict[eachDateString] = eachDict
                    if self.dupPriority == FIRST:
                        break

        print(f'[v] Make Viewer Compare Data Finish : {round(time.time() - start, 2)} sec')
        print('--------------------------------------------------------------')
        print(f'[*] Make Server Compare Data From tempMatchLogList :: {datetime.strftime(datetime.now(), DATETIME_FORMAT)}')
        print(f'[*] Try to matching \'{len(self.tmpMatchingList)} X {len(self.serverOriginLogList)}\' Log Data')
        start = time.time()

        progressPrcnt = 1
        progressMount = 0

        tmpServerDict = {}
        # Server
        for eachDateString in self.tmpMatchingList:
            
            progressMount += 1
            if progressMount >= addMountVal * progressPrcnt:
                print(f'  [>] Data Processing... {progressPrcnt*5:3}%')
                self.RunSuccess()
                progressPrcnt += 1

            for eachDict in self.serverOriginLogList:
                if eachDateString == eachDict['time']:
                    if self.dupPriority == FIRST and tmpServerDict.get(eachDateString):
                        continue
                    tmpServerDict[eachDateString] = eachDict
                    if self.dupPriority == FIRST:
                        break

        print(f'[v] Make Server Compare Data Finish : {round(time.time() - start, 2)} sec')
        print('--------------------------------------------------------------')

        self.cmpServerLogDict = tmpServerDict
        self.cmpViewerLogDict = tmpViewerDict

        return True


    def compareLog(self):
        finalRes = []

        print()
        print('==============================================================')
        print('[*] 매칭 및 부분 매칭을 체크합니다.')
        print('==============================================================')

        allMatching             = 0
        self.invalidVlaueCount  = 0

        for eachLog in self.viewerOriginLogList:
            # MISSING
            if not self.cmpViewerLogDict.get(eachLog['time']):
                finalRes.append(f'[MIS] {eachLog["time"]}')
            # CHECK PARTIAL
            else:
                isUnmatched = False
                unMatchStr  = ""
                for idx, eachKey in enumerate(self.matchCheckKeyList):
                    try:
                        # 문자열 비교
                        if self.keyDetailList[idx] == TYPE_STR:
                            if str(self.cmpViewerLogDict[eachLog['time']][eachKey]) != str(self.cmpServerLogDict[eachLog['time']][eachKey]):
                                isUnmatched = True
                                unMatchStr  += f'/{eachKey}'
                                self.unmatchCountList[idx] += 1
                        # 실수값 비교
                        else:
                            viewerNumVal = float(self.cmpViewerLogDict[eachLog['time']][eachKey])
                            serverNumVal = float(self.cmpServerLogDict[eachLog['time']][eachKey])

                            if fabs(viewerNumVal - serverNumVal) > sys.float_info.epsilon:
                                isUnmatched = True
                                unMatchStr  += f'/{eachKey}'
                                self.unmatchCountList[idx] += 1

                    except Exception:
                        self.invalidVlaueCount += 1
                        finalRes.append(f'[INV/{eachKey}] {eachLog["time"]}')
                        continue

                if isUnmatched is True:
                    finalRes.append(f'[DIF{unMatchStr}] {eachLog["time"]}')
                else:
                    finalRes.append(f'[O] {eachLog["time"]}')
                    allMatching += 1

        print('[v] 체크 완료')
        print('--------------------------------------------------------------')
        print()

        print('==============================================================')
        print('[*] 결과')
        print('==============================================================')
        print(f'[i] time 값 일치된 {len(self.cmpViewerLogDict)} 개 로그 중 불일치 갯수')
        print('[i] 만약 로그 파일 하나에서 speed, bearing 불일치 시 둘 다 카운트됨')
        print('--------------------------------------------------------------')

        for idx, eachKey in enumerate(self.matchCheckKeyList):
            prcnt = round((self.unmatchCountList[idx] / len(self.cmpViewerLogDict))*100, 2)
            print(f'- {self.matchCheckKeyList[idx]:10} 값 불일치 : {self.unmatchCountList[idx]:6} / {len(self.cmpViewerLogDict):6} ( {prcnt:5} % )')

        print('--------------------------------------------------------------')
        print(f'- 체크값 자체가 없는 로그 갯수 : {self.invalidVlaueCount}')
        print('--------------------------------------------------------------')
        prcnt = round((len(self.cmpViewerLogDict) / len(self.viewerOriginLogList))*100, 2)
        print(f'- Time 매칭 성공 로그 갯수 : {len(self.cmpViewerLogDict):6} / {len(self.viewerOriginLogList):6} ( {prcnt:5} % )')

        prcnt = round((allMatching / len(self.cmpViewerLogDict))*100, 2)
        print(f'- 모든 매칭 성공 로그 갯수 : {allMatching:6} / {len(self.cmpViewerLogDict):6} ( {prcnt:5} % )')
        print('--------------------------------------------------------------')

        resultFileFullPath = os.path.join(self.resultSaveDir, RESULT_FILE)
        
        with open(resultFileFullPath, 'w', encoding='utf-8') as wf:
            for eachLine in finalRes:
                wf.write(f'{eachLine}\n')
        
        print(f'[v] 결과를 파일로 저장했습니다. : \'{resultFileFullPath}\'')
        print('--------------------------------------------------------------')
        print()

        self.RunFinish()


# Ui_MainWindow Class (MainWindow)
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
class Ui_MainWindow(object):
    def __init__(self, width, height) -> None:
        self.width  = int(width)
        self.height = int(height)

    def setupUi(self, MainWindow:QMainWindow):
        # 전체
        MainWindow.setObjectName('MainWindow')
        MainWindow.setWindowTitle(f'GPS Log Compare Program / v{VERSION} ({UPDATE})')

        MainWindow.resize(self.width, self.height)
        MainWindow.setFixedSize(self.width, self.height)

        self.centralWidget          = QWidget(MainWindow)
        self.statusBar              = QStatusBar()

        MainWindow.setStatusBar(self.statusBar)
        self.statusBar.showMessage(f'Made by {AUTHOR} :: Source - {GIT_LINK}')

        # 상단
        self.selectPathGroupBox     = QGroupBox('파일 및 폴더 선택', MainWindow)

        self.viewerLogPathLabel     = QLabel('뷰어 로그 파일')
        self.viewerLogPathLineEdit  = QLineEdit('C:/')
        self.viewerLogPathButton    = QPushButton('Edit')

        self.serverLogPathLabel     = QLabel('서버 로그 파일')
        self.serverLogPathLineEdit  = QLineEdit('C:/')
        self.serverLogPathButton    = QPushButton('Edit')

        self.resultDirLabel         = QLabel('결과 저장 폴더')
        self.resultDirLineEdit      = QLineEdit(CUR_PATH)
        self.resultDirButton        = QPushButton('Edit')

        self.top_V_Layout           = QVBoxLayout()
        self.top_upper_H_Layout     = QHBoxLayout()
        self.top_mddle_H_Layout     = QHBoxLayout()
        self.top_under_H_Layout     = QHBoxLayout()

        self.top_upper_H_Layout.addWidget(self.viewerLogPathLabel, 1)
        self.top_upper_H_Layout.addWidget(self.viewerLogPathLineEdit, 4)
        self.top_upper_H_Layout.addWidget(self.viewerLogPathButton, 1)

        self.top_mddle_H_Layout.addWidget(self.serverLogPathLabel, 1)
        self.top_mddle_H_Layout.addWidget(self.serverLogPathLineEdit, 4)
        self.top_mddle_H_Layout.addWidget(self.serverLogPathButton, 1)

        self.top_under_H_Layout.addWidget(self.resultDirLabel, 1)
        self.top_under_H_Layout.addWidget(self.resultDirLineEdit, 4)
        self.top_under_H_Layout.addWidget(self.resultDirButton, 1)

        self.top_V_Layout.addLayout(self.top_upper_H_Layout)
        self.top_V_Layout.addLayout(self.top_mddle_H_Layout)
        self.top_V_Layout.addLayout(self.top_under_H_Layout)

        self.selectPathGroupBox.setLayout(self.top_V_Layout)        

        # 상단 세팅
        self.viewerLogPathLineEdit.setReadOnly(True)
        self.serverLogPathLineEdit.setReadOnly(True)
        self.resultDirLineEdit.setReadOnly(True)

        # 중단
        self.optionGroupBox         = QGroupBox('Option Setting', MainWindow)

        self.dateTimeFormatLabel    = QLabel('Time 형식')
        self.dateTimeFormatLineEdit = QLineEdit(DATETIME_FORMAT)

        self.checkLogKeyLabel       = QLabel('로그 체크값')
        self.checkLogKeyLineEdit    = QLineEdit(', '.join(MATCH_CHECK_LIST))
        self.checkLogKeyButton      = QPushButton('Edit')

        self.mid_V_Layout           = QVBoxLayout()
        self.mid_upper_H_Layout     = QHBoxLayout()
        self.mid_under_H_Layout     = QHBoxLayout()

        self.mid_upper_H_Layout.addWidget(self.dateTimeFormatLabel, 1)
        self.mid_upper_H_Layout.addWidget(self.dateTimeFormatLineEdit, 5)

        self.mid_under_H_Layout.addWidget(self.checkLogKeyLabel, 1)
        self.mid_under_H_Layout.addWidget(self.checkLogKeyLineEdit, 4)
        self.mid_under_H_Layout.addWidget(self.checkLogKeyButton, 1)

        self.mid_V_Layout.addLayout(self.mid_upper_H_Layout)
        self.mid_V_Layout.addLayout(self.mid_under_H_Layout)

        self.optionGroupBox.setLayout(self.mid_V_Layout)

        self.dateTimeFormatLineEdit.setDisabled(True)
        self.checkLogKeyLineEdit.setDisabled(True)
        self.checkLogKeyLineEdit.setReadOnly(True)
        self.checkLogKeyButton.setDisabled(True)

        # 중단 2
        self.priorityGroupBox       = QGroupBox('중복시 파일 비교 우선값', MainWindow)
        self.priorityFirstRButton   = QRadioButton(FIRST)
        self.priorityLastRButton    = QRadioButton(LAST)

        self.mid2_H_left_Layout     = QHBoxLayout()
        self.mid2_H_left_Layout.addWidget(self.priorityFirstRButton)
        self.mid2_H_left_Layout.addWidget(self.priorityLastRButton)

        self.checkBoxGroupBox       = QGroupBox('기타 옵션', MainWindow)
        self.fixSettingCheckBox     = QCheckBox('세팅 값 고정')
        self.openResultDirCheckBox  = QCheckBox('완료 시 결과 폴더 열기')

        self.mid2_H_right_Layout    = QHBoxLayout()
        self.mid2_H_right_Layout.addWidget(self.fixSettingCheckBox)
        self.mid2_H_right_Layout.addWidget(self.openResultDirCheckBox)

        self.priorityGroupBox.setLayout(self.mid2_H_left_Layout)
        self.checkBoxGroupBox.setLayout(self.mid2_H_right_Layout)

        self.mid2_H_Layout          = QHBoxLayout()
        self.mid2_H_Layout.addWidget(self.priorityGroupBox)
        self.mid2_H_Layout.addWidget(self.checkBoxGroupBox)

        self.priorityFirstRButton.setChecked(True)
        self.fixSettingCheckBox.toggle()

        # 진행바 그룹박스
        self.progressGroupBox       = QGroupBox('진행 상황')
        self.progress_H_Layout      = QHBoxLayout()
        self.progressBar            = QProgressBar()
        self.progress_H_Layout.addWidget(self.progressBar)
        self.progressGroupBox.setLayout(self.progress_H_Layout)

        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progressBar.setValue(0)

        # 하단
        self.bot_H_Layout           = QHBoxLayout()

        self.LogTextEdit            = QTextEdit()
        self.FileCheckButton        = QPushButton('파일 유효성 체크')
        self.RunButton              = QPushButton('Run')

        self.bot_H_Layout.addWidget(self.FileCheckButton, 1)
        self.bot_H_Layout.addWidget(self.RunButton,   1)

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget(self.selectPathGroupBox, 1)
        self.mainLayout.addWidget(self.optionGroupBox, 1)
        self.mainLayout.addLayout(self.mid2_H_Layout, 1)
        self.mainLayout.addWidget(self.progressGroupBox)
        self.mainLayout.addWidget(self.LogTextEdit, 5)
        self.mainLayout.addLayout(self.bot_H_Layout, 1)

        self.centralWidget.setLayout(self.mainLayout)
        MainWindow.setCentralWidget(self.centralWidget)

        self.RunButton.setDisabled(True)


class CompareProgramUI(QMainWindow):
    def __init__(self, QApp=None, width=WINDOW_WIDTH, height=WINDOW_HEIGHT):
        super().__init__()
        self.app                = QApp

        self.viewerLogPath      = r""
        self.serverLogPath      = r""
        self.resultDir          = r""

        self.pgSignal           = ProgressSignal()
        self.compareApp         = CompareProgram(self.pgSignal)
        self.DataExtractThread  = DataExtractThread(self)

        self.threadRunSuccess   = False

        self.ui                 = Ui_MainWindow(width, height)
        self.ui.setupUi(self)

        self.dlg                = LogKeySettingDlg(self.compareApp, width, height/2)

        self.initialize()

    def TRACE(self, log=''):
        self.ui.LogTextEdit.append(log)
        print(log)

    def noticeHowToRun(self):
        self.TRACE(" ")
        self.TRACE("[ 프로그램 실행 방법 ]")
        self.TRACE("-------------------------------------------------------------------")
        self.TRACE("1. 파일 및 폴더 선택을 완료해 주세요")
        self.TRACE("2. 옵션 세팅의 변경이 필요하다면 변경해 주세요")
        self.TRACE("3. \'파일 유효성 체크\' 버튼을 눌러주세요")
        self.TRACE("4. 뷰어 및 서버 로그 파일이 유효하다면 \'Run\'버튼이 활성화됩니다.")
        self.TRACE("5. \'Run\' 버튼을 눌러 로그 비교를 실행해주세요.")
        self.TRACE("-------------------------------------------------------------------")
        self.TRACE()
        self.TRACE("[ 결과 파일 Prefix ]")
        self.TRACE("-------------------------------------------------------------------")
        self.TRACE("[INV]   - 로그 내 특정 값 자체가 유효하지 않음")
        self.TRACE("[DIF]   - 로그 내 특정 값이 다름")
        self.TRACE("[MIS]   - 누락")
        self.TRACE("[O]     - 모두 매칭됨")
        self.TRACE("-------------------------------------------------------------------")
        self.TRACE()
    


    def selectViewerLogFile(self):
        prePath     = self.ui.viewerLogPathLineEdit.text()
        targetFile  = QFileDialog.getOpenFileName(self, 'Select ViewerLog File', CUR_PATH)[0]

        if len(targetFile) == 0:
            targetFile = prePath
        else:
            self.TRACE(f"* 뷰어 로그 파일 선택 완료 : {targetFile}")

        self.ui.viewerLogPathLineEdit.setText(targetFile)
        self.viewerLogPath = targetFile


    def selectServerLogFile(self):
        prePath     = self.ui.serverLogPathLineEdit.text()
        targetFile  = QFileDialog.getOpenFileName(self, 'Select ServerLog File', CUR_PATH)[0]

        if len(targetFile) == 0:
            targetFile = prePath
        else:
            self.TRACE(f"* 서버 로그 파일 선택 완료 : {targetFile}")

        self.ui.serverLogPathLineEdit.setText(targetFile)
        self.serverLogPath = targetFile


    def selectResultDir(self):
        prePath     = self.ui.resultDirLineEdit.text()
        targetDir   = QFileDialog.getExistingDirectory(self, 'Select Result Folder', CUR_PATH)

        if len(targetDir) == 0:
            targetDir = prePath
        else:
            self.TRACE(f'* 결과 디렉토리 세팅 완료 : {targetDir}')

        self.ui.resultDirLineEdit.setText(targetDir)
        self.resultDir = targetDir


    def isValidLogKeyList(self, sListString:str):
        checkString = sListString.strip()
        if checkString[0] == ',' or checkString[-1] == ',':
            return False
        return True


    def onChangeDateFormat(self, txt:str):
        self.compareApp.dateTimeFormat = txt
        self.ui.RunButton.setDisabled(True)


    # Not Use
    def onChangeLogKeyList(self, listString:str):
        self.TRACE(f'[>] {listString}')
        self.ui.RunButton.setDisabled(True)


    def checkFiles(self):
        self.TRACE()
        if self.compareApp.setLogFiles(self.viewerLogPath, self.serverLogPath, self.compareApp.matchCheckKeyList) is False:
            self.TRACE("[!] 파일 유효성 체크가 실패했습니다. 로그 파일들을 다시 확인해 주세요.")
        else:
            self.TRACE("[v] 파일 유효성 체크 성공. Run 버튼이 활성화 됩니다.")
            self.TRACE()
            self.TRACE("-------------------------------------------------------------------")
            self.TRACE(f'VIEWER LOG : {self.compareApp.viewerOriginLogList[0]["time"]} ~ {self.compareApp.viewerOriginLogList[-1]["time"]}')
            self.TRACE(f'SERVER LOG : {self.compareApp.serverOriginLogList[0]["time"]} ~ {self.compareApp.serverOriginLogList[-1]["time"]}')
            self.TRACE("-------------------------------------------------------------------")
            self.TRACE()
            self.ui.RunButton.setEnabled(True)


    def setDupPriority(self):
        if self.ui.priorityFirstRButton.isChecked() is True:
            self.compareApp.dupPriority = FIRST
        else:
            self.compareApp.dupPriority = LAST


    def onChangeFixSetting(self):
        if self.ui.fixSettingCheckBox.isChecked() is True:
            self.ui.dateTimeFormatLineEdit.setDisabled(True)
            self.ui.checkLogKeyLineEdit.setDisabled(True)
            self.ui.checkLogKeyButton.setDisabled(True)
        else:
            self.ui.dateTimeFormatLineEdit.setEnabled(True)
            self.ui.checkLogKeyLineEdit.setEnabled(True)
            self.ui.checkLogKeyButton.setEnabled(True)


    @pyqtSlot()
    def runCompProgram(self):
        self.ui.RunButton.setDisabled(True)
        self.ui.fixSettingCheckBox.setDisabled(True)

        self.TRACE()
        self.TRACE("[#] 프로그램을 실행합니다.")

        self.compareApp.resultSaveDir = self.resultDir
        self.setDupPriority()

        self.TRACE(f"[i] 로그 체크값 : {self.compareApp.matchCheckKeyList}")
        self.TRACE()

        self.compareApp.InitRunStage(1 + 1 + 20 + 20 + 1)

        self.TRACE(f'[#] 중복값 체크 실행 :: {datetime.now()}')
        self.compareApp.findDuplicateLogByServer()

        self.TRACE(f'[#] 누락값 체크 실행 :: {datetime.now()}')
        self.compareApp.findMissingLogCompareServerAndViewer()

        self.TRACE(f'[#] 로그값 매칭 실행 :: {datetime.now()}')
        self.DataExtractThread.start()


    @pyqtSlot(int)
    def updateProgressBar(self, progressVal):
        self.ui.progressBar.setValue(progressVal)

    
    @pyqtSlot()
    def onFinishDataExtractThread(self):
        if self.threadRunSuccess is True:
            self.TRACE("[#] 데이터 정제가 끝나 비교를 시작합니다.")
            self.compareApp.compareLog()
            self.TRACE(f"[v] 로그값 매칭 완료. 결과를 \'{os.path.join(self.resultDir, RESULT_FILE)}\' 에 저장했습니다.")
            self.TRACE("[#] 프로그램의 실행이 완료되었습니다. 결과 파일을 확인해 주세요!")
            self.TRACE()

            if self.ui.openResultDirCheckBox.isChecked() is True:
                os.startfile(self.compareApp.resultSaveDir)
        else:
            self.compareApp.RunFail('[!] 데이터 정제가 실패하여 로그 매칭을 할 수 없습니다. 파일을 다시 확인해주세요.')

        self.ui.fixSettingCheckBox.setEnabled(True)


    def openDlg(self):
        self.dlg.setTableByParentData()
        self.dlg.show()

    def accpetApply(self):
            self.TRACE('[#] 로그 체크값 변경')
            self.compareApp.matchCheckKeyList   = self.dlg.getDlgChangedKeyNameList()
            self.compareApp.keyDetailList       = self.dlg.getDlgChangedKeyTypeList()
            self.ui.checkLogKeyLineEdit.setText(', '.join(self.compareApp.matchCheckKeyList))

    def rejectApply(self):
        self.TRACE('[#] 로그 체크값 변경 취소')

    def initialize(self):
        self.noticeHowToRun()

        self.ui.viewerLogPathButton.clicked.connect(self.selectViewerLogFile)
        self.ui.serverLogPathButton.clicked.connect(self.selectServerLogFile)
        self.ui.resultDirButton.clicked.connect(self.selectResultDir)

        self.ui.dateTimeFormatLineEdit.textChanged[str].connect(self.onChangeDateFormat)
        self.ui.checkLogKeyLineEdit.textChanged[str].connect(self.onChangeLogKeyList)

        self.ui.FileCheckButton.clicked.connect(self.checkFiles)
        self.ui.RunButton.clicked.connect(self.runCompProgram)

        self.ui.fixSettingCheckBox.stateChanged.connect(self.onChangeFixSetting)
        self.pgSignal.signal.connect(self.updateProgressBar)
        self.DataExtractThread.finished.connect(self.onFinishDataExtractThread)

        self.ui.checkLogKeyButton.clicked.connect(self.openDlg)

        self.dlg.accepted.connect(self.accpetApply)
        self.dlg.rejected.connect(self.rejectApply)

    def run(self):
        self.show()
        self.app.exec()


# LogKeySettingTable Dialog
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
class LogKeySettingDlg(QDialog):
    def __init__(self, parent:CompareProgram, width, height):
        super().__init__()

        self.p          = parent
        self._width     = int(width)
        self._height    = int(height)
        self._tableRows = self.getTableRowNumFromParent()

        self.tmpKeyNameList = self.p.matchCheckKeyList.copy()
        self.tmpKeyTypeList = self.p.keyDetailList.copy()

        self.setupUI()


    def setupUI(self):
        self.resize(self._width, self._height)
        self.setFixedSize(self._width, self._height)
        self.setWindowTitle('로그 체크값 설정')

        self.tableGroupBox  = QGroupBox('Setting Table')
        self.keyTable       = QTableWidget()
        self.tableLayout    = QHBoxLayout()
        self.tableLayout.addWidget(self.keyTable)
        self.tableGroupBox.setLayout(self.tableLayout)

        self.addButton      = QPushButton('추가')
        self.delButton      = QPushButton('제거')

        self.OKButton       = QPushButton('확인')
        self.CancelButton   = QPushButton('취소')

        self.btn_upper_H_Layout = QHBoxLayout()
        self.btn_under_H_Layout = QHBoxLayout()
        self.btn_V_Layout       = QVBoxLayout()

        self.btn_upper_H_Layout.addWidget(self.addButton)
        self.btn_upper_H_Layout.addWidget(self.delButton)
        self.btn_under_H_Layout.addWidget(self.OKButton)
        self.btn_under_H_Layout.addWidget(self.CancelButton)

        self.btn_V_Layout.addLayout(self.btn_upper_H_Layout)
        self.btn_V_Layout.addLayout(self.btn_under_H_Layout)

        self.MainLayout = QVBoxLayout()
        self.MainLayout.addWidget(self.tableGroupBox, 5)
        self.MainLayout.addLayout(self.btn_V_Layout, 1)

        self.setLayout(self.MainLayout)

        # Setting
        self.keyTable.resize(int(self._width/2), int(self._height*0.75))
        self.keyTable.setColumnCount(DLG_HEADER_LEN)
        self.keyTable.setHorizontalHeaderLabels(['이름', '타입'])
        self.keyTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.setTableByParentData()

        header = self.keyTable.horizontalHeader()
        for col in range(header.count()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(col, int(self._width * 0.4))

        # Connect
        self.delButton.clicked.connect(self.delEvent)
        self.addButton.clicked.connect(self.addEvent)
        self.OKButton.clicked.connect(self.accept)
        self.CancelButton.clicked.connect(self.reject)

    def setTableByParentData(self):
        self._tableRows = self.getTableRowNumFromParent()

        self.keyTable.clearContents()
        self.keyTable.setRowCount(self._tableRows)

        self.tmpKeyNameList = self.p.matchCheckKeyList.copy()
        self.tmpKeyTypeList = self.p.keyDetailList.copy()

        self.refresh()

    def refresh(self):
        for idxRow in range(self._tableRows):
            self.keyTable.setCellWidget(idxRow, DLG_IDX_NAME, QLineEdit(self.tmpKeyNameList[idxRow]))
            self.keyTable.setCellWidget(idxRow, DLG_IDX_TYPE, QComboBox())

            self.keyTable.cellWidget(idxRow, DLG_IDX_TYPE).addItems(TYPE_TABLE)
            self.keyTable.cellWidget(idxRow, DLG_IDX_TYPE).setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.keyTable.cellWidget(idxRow, DLG_IDX_TYPE).setCurrentIndex(self.tmpKeyTypeList[idxRow])

    def getTableRowNumFromParent(self):
        return len(self.p.matchCheckKeyList)

    def getCurrentTableRows(self):
        return self.keyTable.rowCount()

    def delEvent(self):
        selectRow = self.keyTable.currentRow()
        reply = QMessageBox.question(self, 
                                     '로그 체크값 삭제', 
                                     f'정말로 체크값 \'{self.tmpKeyNameList[selectRow]}\'를 삭제하시겠습니까?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.keyTable.removeRow(selectRow)
            self.tmpKeyNameList.pop(selectRow)
            self.tmpKeyTypeList.pop(selectRow)
            self._tableRows -= 1
            self.keyTable.setRowCount(self._tableRows)
            self.refresh()

    def addTableRowData(self, nameData:str):
        self._tableRows += 1
        self.keyTable.setRowCount(self._tableRows)
        self.tmpKeyNameList.append(nameData)
        self.tmpKeyTypeList.append(TYPE_STR)
        self.refresh()

    def addEvent(self):
        name, ok = QInputDialog.getText(self, '로그 체크값 입력', '[New] 등록할 로그 체크값의 이름을 적어주세요 : ')
        if ok:
            self.addTableRowData(str(name))

    def getDlgChangedKeyNameList(self):
        resList = []
        for eachRow in range(self.getCurrentTableRows()):
            resList.append(str(self.keyTable.cellWidget(eachRow, DLG_IDX_NAME).text()))
        return resList

    def getDlgChangedKeyTypeList(self):
        resList = []
        for eachRow in range(self.getCurrentTableRows()):
            resList.append(self.keyTable.cellWidget(eachRow, DLG_IDX_TYPE).currentIndex())
        return resList            


# Common Use Class : PyQt Thread
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
class DataExtractThread(QThread):
    def __init__(self, parent:CompareProgramUI):
        super().__init__(parent)
        self.p      = parent
        self.target = parent.compareApp

    def run(self):
        self.p.threadRunSuccess = False
        if self.target.makeCompareDictFromTmpMatchingList() is True:
            self.p.threadRunSuccess = True


if __name__ == "__main__":
    App             = QApplication(sys.argv)
    if USE_PYQT5 is True:
        ScreenSize      = App.desktop().screenGeometry()
        AppWidth        = ScreenSize.width()*(1/4)
        AppHeight       = ScreenSize.width()*(2/5)
    else:
        AppWidth        = WINDOW_WIDTH
        AppHeight       = WINDOW_HEIGHT
    CompApp         = CompareProgramUI(App, AppWidth, AppHeight)
    CompApp.run()