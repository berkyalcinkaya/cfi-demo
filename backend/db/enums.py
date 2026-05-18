from enum import Enum


class MorphokineticStage(str, Enum):
    t1 = "t1"
    tPN = "tPN"
    tPNf = "tPNf"
    t2 = "t2"
    t3 = "t3"
    t4 = "t4"
    t5 = "t5"
    t6 = "t6"
    t7 = "t7"
    t8 = "t8"
    tM = "tM"
    tB = "tB"
    tEB = "tEB"
    tEmpty = "tEmpty"


class PloidyClass(str, Enum):
    euploid = "euploid"
    aneuploid = "aneuploid"
    mosaic = "mosaic"
