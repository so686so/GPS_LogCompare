# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- #
TITLE       = 'GPS Log Compare Program for GNET System'
VERSION     = '1.0.0'
AUTHOR      = 'So Byung Jun'
UPDATE      = '2022-6-14'
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
from msilib.schema import SelfReg
import  os
import  sys
import  shutil
import  time
from    datetime                import datetime, timedelta

# Installed Library
# -------------------------------------------------------------------
from    chardet                 import detect      
from    iteration_utilities     import unique_everseen, duplicates

# For GUI ( Ver. PyQt 6.2.2 )
# -------------------------------------------------------------------
from    PyQt6                   import QtCore, QtGui, QtWidgets
from    PyQt6.QtCore            import *
from    PyQt6.QtGui             import *
from    PyQt6.QtWidgets         import *
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-


# Const Define
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
# 중복값 매칭 시 우선순위 조절 위한 값
FIRST = '최초값 우선'
LAST  = '마지막값 우선'

# 강제 종료 시나리오별 리턴 값
EXIT_ERROR_NOT_SET_FILE  = 1
EXIT_ERROR_DATE_TRANS    = 2
EXIT_LOAD_FILE_FAIL      = 3

# 텍스트 파일 불러올 때 유효한 인코딩 값
VALID_ENCODING_FORMAT   = [ 'utf-8', 'ascii', 'ecu-kr', 'cp949' ]

# 기타 Const
ENCODING_PREPIX         = 'ENC_'
CUR_PATH                = os.path.dirname('./')

WINDOW_WIDTH            = 800
WINDOW_HEIGHT           = 650

# Var Define
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
# 중복값 매칭 우선순위
DUPLICATE_PRIORITY  = FIRST

# 인코딩 컨버트할 때 변환할 포맷
CONVERT_ENCODING    = 'utf-8'

# 파일 경로들
VIEWER_FILE         = './viewer.txt'
SERVER_FILE         = './server.txt'
RESULT_DIR          = CUR_PATH
RESULT_FILE         = 'Result.txt'

# 매치 체크할 때 검사할 키값 목록
MATCH_CHECK_LIST    = ['time', 'speed', 'bearing', 'latitude', 'longitude' ]
UNMATCH_COUNT_LIST  = [ 0 for _ in MATCH_CHECK_LIST ]

# DateTime StringFormat
DATETIME_FORMAT     = "%Y-%m-%d %H:%M:%S"


# FileChecker : FileCheck 및 인코딩 체크, 인코딩 변환 및 Json Read
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
class FileChecker:
    def __init__( self, convert_encoding = CONVERT_ENCODING ):
        self.__targetFile       = r""
        self.__targetFormat     = None

        self.__convertFile      = r""
        self.__convertFormat    = convert_encoding
        
        self.__isDoneCorrect    = False
        self.__isValidJson      = False
        self.__newCorrectJson   = False

        self.__jsonObject       = None

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
    def isValidJson(self):
        return self.__isValidJson

    @isValidJson.setter
    def isValidJson(self, bVal:bool):
        self.__isValidJson = bVal


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
            print('[!] 아직 파일을 등록하지 않았습니다. 파일을 등록해주세요.')
            return False
        
        if not self.targetFormat:
            print("[!] 타겟 파일의 인코딩 형식을 불러올 수 없습니다. 파일을 UTF-8 로 저장하는 것을 권장합니다.")
            return False

        baseName = os.path.basename(self.targetFile)
        destFile = f'./{ENCODING_PREPIX}{baseName}'

        if self.targetFormat == self.convertFormat:
            shutil.copyfile(self.targetFile, destFile)

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


    # JsonRead 를 하려 했는데, 파일의 괄호가 알맞게 작성되어있지 않는 경우에 자동 보정
    def correctionWorkForReadJson(self):
        if not self.convertFile:
            print('[!] 인코딩 형식 변환된 파일이 없습니다.')
            return False

        print(f'[#] Json read 를 위한 파일 보정 체크 : {self.convertFile}')

        lineList = ""
        with open(self.convertFile, 'r', encoding=self.convertFormat) as rf:
            lineList = rf.readlines()

        lastLine = lineList[-1].strip()

        if  lastLine[-1] == ',':
            lineList[-1] = lineList[-1].replace(',', ']]')

            print(f'[#] \'{self.targetFile}\' 이 Json read 에 적합하지 않아 보정을 시도합니다.')

            try:
                with open(self.convertFile, 'w', encoding=self.convertFormat) as wf:
                    for line in lineList:
                        wf.write(line)
                print('[v] 보정 완료.')
            except Exception:
                print("[!] 보정 실패. 직접 메모장의 마지막 부분을 수정해 주세요. 괄호의 쌍이 맞아야 합니다.")
                return False

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
        if os.path.isfile(self.convertFile):
            os.remove(self.convertFile)


# CompareProgram : FileCheck로 로그파일을 불러와서 실제 비교하는 클래스
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
class CompareProgram:
    def __init__(self) -> None:
        self.__dateTimeFormat       = DATETIME_FORMAT
        self.__matchCheckKeyList    = MATCH_CHECK_LIST
        self.__unmatchCountList     = [ 0 for _ in MATCH_CHECK_LIST ]
        self.__invalidVlaueCount    = 0
        self.__resultSaveDir        = RESULT_DIR
        self.__dupPriority          = DUPLICATE_PRIORITY

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


    def setLogFiles(self, vFile=VIEWER_FILE, sFile=SERVER_FILE):
        self.viewerOriginLogList.clear()
        self.serverOriginLogList.clear()

        vf = FileChecker()
        self.viewerOriginLogList = vf.registerNewFile(vFile).readJsonFile()

        sf = FileChecker()
        self.serverOriginLogList = sf.registerNewFile(sFile).readJsonFile()

        if not self.viewerOriginLogList:
            print("[!] 뷰어 로그 파일이 유효하지 않습니다.")
            return False

        if not self.serverOriginLogList:
            print("[!] 서버 로그 파일이 유효하지 않습니다.")
            return False

        print()
        print('--------------------------------------------------------------')
        print(f'[v] LogFile 세팅 완료 : \'{vFile}\' & \'{sFile}\'')
        print('--------------------------------------------------------------')

        if self.checkDateTimeFormatOK() is False:
            return False

        if self.checkKeyListOK() is False:
            return False

        self.setDateTimeList()
        return True

    def checkDateTimeFormatOK(self):
        try:
            _ = self.convertDateStringToDateTime(self.serverOriginLogList[0]['time'])
            return True
        except Exception:
            print()
            print('[!] 입력한 Time 형식이 유효하지 않습니다. 다시 입력해 주세요.')
            return False


    def checkKeyListOK(self):
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


    def makeCompareDictFromTmpMatchingList(self):
        print()
        print('==============================================================')
        print('[*] 매칭 및 부분 매칭을 체크하기 위한 데이터를 정제합니다. 해당 작업은 시간이 오래 걸릴 수 있습니다.')
        print('==============================================================')

        if not self.tmpMatchingList:
            print('[!] 누락 체크 후 임시 매칭된 데이터 자료가 없습니다. 누락 체크를 하거나 로그 파일을 확인해주세요')
            return False

        print(f'[*] Make Viewer Compare Data From tempMatchLogList :: {datetime.now()}')
        start = time.time()

        progressPrcnt = 1
        progressMount = 0
        addMountVal   = len(self.tmpMatchingList) / 10

        tmpViewerDict = {}
        # Viewer
        for eachDateString in self.tmpMatchingList:
            
            progressMount += 1
            if progressMount >= addMountVal * progressPrcnt:
                print(f'  [>] Data Processing... {progressPrcnt*10:3}%')
                progressPrcnt += 1

            for eachDict in self.viewerOriginLogList:
                if eachDateString == eachDict['time']:
                    if  self.dupPriority == FIRST and tmpViewerDict.get(eachDateString):
                        continue
                    tmpViewerDict[eachDateString] = eachDict

        print(f'[v] Make Viewer Compare Data Finish : {round(time.time() - start, 2)} sec')

        print('--------------------------------------------------------------')
        print(f'[*] Make Server Compare Data From tempMatchLogList :: {datetime.now()}')
        start = time.time()

        progressPrcnt = 1
        progressMount = 0

        tmpServerDict = {}
        # Viewer
        for eachDateString in self.tmpMatchingList:
            
            progressMount += 1
            if progressMount >= addMountVal * progressPrcnt:
                print(f'  [>] Data Processing... {progressPrcnt*10:3}%')
                progressPrcnt += 1

            for eachDict in self.serverOriginLogList:
                if eachDateString == eachDict['time']:
                    if self.dupPriority == FIRST and tmpServerDict.get(eachDateString):
                        continue
                    tmpServerDict[eachDateString] = eachDict

        print(f'[v] Make Server Compare Data Finish : {round(time.time() - start, 2)} sec')
        print('--------------------------------------------------------------')

        self.cmpServerLogDict = tmpServerDict
        self.cmpViewerLogDict = tmpViewerDict

        return True


    def compareLog(self):
        if self.makeCompareDictFromTmpMatchingList() is False:
            return

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
            # CHECK PARTIAL?
            else:
                isUnmatched = False
                unMatchStr  = ""
                for idx, eachKey in enumerate(self.matchCheckKeyList):
                    try:
                        if self.cmpViewerLogDict[eachLog['time']][eachKey] != self.cmpServerLogDict[eachLog['time']][eachKey]:
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
        print(f'- 부분 매칭 성공 로그 갯수 : {len(self.cmpViewerLogDict):6} / {len(self.viewerOriginLogList):6} ( {prcnt:5} % )')

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


# Ui_MainWindow Class (MainWindow)
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
class Ui_MainWindow(object):
    def setupUi(self, MainWindow:QMainWindow):
        # 전체
        MainWindow.setObjectName('MainWindow')
        MainWindow.setWindowTitle('GPS Log Compare Program')

        MainWindow.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        MainWindow.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        MainWindow.statusBar().showMessage(f'v{VERSION} ({UPDATE})')

        self.centralWidget          = QWidget(MainWindow)

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

        self.top_upper_H_Layout.addWidget(self.viewerLogPathLabel, 2)
        self.top_upper_H_Layout.addWidget(self.viewerLogPathLineEdit, 3)
        self.top_upper_H_Layout.addWidget(self.viewerLogPathButton, 1)

        self.top_mddle_H_Layout.addWidget(self.serverLogPathLabel, 2)
        self.top_mddle_H_Layout.addWidget(self.serverLogPathLineEdit, 3)
        self.top_mddle_H_Layout.addWidget(self.serverLogPathButton, 1)

        self.top_under_H_Layout.addWidget(self.resultDirLabel, 2)
        self.top_under_H_Layout.addWidget(self.resultDirLineEdit, 3)
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

        self.mid_V_Layout           = QVBoxLayout()
        self.mid_upper_H_Layout     = QHBoxLayout()
        self.mid_under_H_Layout     = QHBoxLayout()

        self.mid_upper_H_Layout.addWidget(self.dateTimeFormatLabel, 2)
        self.mid_upper_H_Layout.addWidget(self.dateTimeFormatLineEdit, 4)

        self.mid_under_H_Layout.addWidget(self.checkLogKeyLabel, 2)
        self.mid_under_H_Layout.addWidget(self.checkLogKeyLineEdit, 4)

        self.mid_V_Layout.addLayout(self.mid_upper_H_Layout)
        self.mid_V_Layout.addLayout(self.mid_under_H_Layout)

        self.optionGroupBox.setLayout(self.mid_V_Layout)

        self.dateTimeFormatLineEdit.setDisabled(True)
        self.checkLogKeyLineEdit.setDisabled(True)

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
        self.mainLayout.addWidget(self.LogTextEdit, 5)
        self.mainLayout.addLayout(self.bot_H_Layout, 1)

        self.centralWidget.setLayout(self.mainLayout)
        MainWindow.setCentralWidget(self.centralWidget)

        self.RunButton.setDisabled(True)


class CompareProgramUI(QMainWindow):
    def __init__(self, QApp=None):
        super().__init__()
        self.app                = QApp

        self.viewerLogPath      = r""
        self.serverLogPath      = r""
        self.resultDir          = r""

        self.compareApp         = CompareProgram()

        self.ui                 = Ui_MainWindow()
        self.ui.setupUi(self)

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

        print(targetFile)

        if len(targetFile) == 0:
            targetFile = prePath
        else:
            self.TRACE(f"* 뷰어 로그 파일 선택 완료 : {targetFile}")

        self.ui.viewerLogPathLineEdit.setText(targetFile)
        self.viewerLogPath = targetFile


    def selectServerLogFile(self):
        prePath     = self.ui.serverLogPathLineEdit.text()
        targetFile  = QFileDialog.getOpenFileName(self, 'Select ServerLog File', CUR_PATH)[0]

        print(targetFile)

        if len(targetFile) == 0:
            targetFile = prePath
        else:
            self.TRACE(f"* 서버 로그 파일 선택 완료 : {targetFile}")

        self.ui.serverLogPathLineEdit.setText(targetFile)
        self.serverLogPath = targetFile


    def selectResultDir(self):
        prePath     = self.ui.resultDirLineEdit.text()
        targetDir   = QFileDialog.getExistingDirectory(self, 'Select Path', CUR_PATH)

        if len(targetDir) == 0:
            targetDir = prePath
        else:
            self.TRACE(f'* 결과 디렉토리 세팅 완료 : {targetDir}')

        self.ui.resultDirLineEdit.setText(targetDir)
        self.resultDir = targetDir


    def onChangeDateFormat(self, txt:str):
        self.compareApp.dateTimeFormat = txt
        self.ui.RunButton.setDisabled(True)


    def onChangeLogKeyList(self, listString:str):
        sList = listString.split(',')
        sList = [ each.strip() for each in sList ]

        self.compareApp.matchCheckKeyList = sList
        self.compareApp.unmatchCountList = [ 0 for _ in sList ]
        self.ui.RunButton.setDisabled(True)


    def checkFiles(self):
        self.TRACE()
        if self.compareApp.setLogFiles(self.viewerLogPath, self.serverLogPath) is False:
            self.TRACE("[!] 파일 유효성 체크가 실패했습니다. 로그 파일들을 다시 확인해 주세요.")
        else:
            self.TRACE("[v] 파일 유효성 체크 성공. Run 버튼이 활성화 됩니다.")
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
        else:
            self.ui.dateTimeFormatLineEdit.setEnabled(True)
            self.ui.checkLogKeyLineEdit.setEnabled(True)


    def runCompProgram(self):
        self.TRACE()
        self.TRACE("[#] 프로그램을 실행합니다.")

        self.compareApp.resultSaveDir = self.resultDir
        self.setDupPriority()

        self.TRACE(f"[i] 로그 체크값 : {self.compareApp.matchCheckKeyList}")
        self.TRACE()

        self.compareApp.findDuplicateLogByServer()
        self.compareApp.findMissingLogCompareServerAndViewer()
        self.compareApp.compareLog()

        self.TRACE("[v] 프로그램 끝")
        self.ui.RunButton.setDisabled(True)

        if self.ui.openResultDirCheckBox.isChecked() is True:
            os.startfile(self.compareApp.resultSaveDir)


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


    def run(self):
        self.show()
        self.app.exec()


if __name__ == "__main__":
    App             = QApplication(sys.argv)
    CompApp         = CompareProgramUI(App)
    CompApp.run()