#!/bin/bash

WORD=$1
WORDS_HISTORY_LOG="words_history.log"

date >> $WORDS_HISTORY_LOG
trans :cs $WORD| tail -2 | tee -a $WORDS_HISTORY_LOG

