#!/bin/bash
#=============================================================================================#
# Script.............: /opt/ptb-performance-client/ptb-performance-client-daemon.sh           #
#                                                                                             #
# Description..........: Controls the execution of ptb-measure-client.pyc tool                #
#                                                                                             #
# Autor..............: Fernando Monje (fcardoso@cleartech.com.br)                             #
# Data Criacao.......: 18/09/2018                                                             #
# Data Modificacao...: 18/09/2018                                                             #
#                                                                                             #
#=============================================================================================#
function stop() {

  echo "Stopping ptb-measure-client.pyc ..."

  ps aux|grep ptb-measure-client.pyc |grep -v grep| grep -v tail|awk '{print $2}'|while read pid; do
    kill $pid
  done
  INTERNAL_STATUS=`__internal_stop_status`
  if [ ${INTERNAL_STATUS} -eq 0 ]; then
    echo "Stopped ..."
  else
    echo "Failed to Stop. Please check the log files ..."
  fi

}

function status() {

  pcount=`ps aux|grep ptb-measure-client.pyc |grep -v grep| grep -v tail|wc -l`
  if [ ${pcount} -eq 0 ]; then
    echo "ptb-measure-client.pyc is not running ..."
  elif [ ${pcount} -eq 1 ]; then
    echo "ptb-measure-client.pyc is running ..."
  else
    echo "Failed to get the correct number of process for ptb-measure-client.pyc."
    echo "Please check the total instances of process manually."
  fi
}

function __internal_start_status() {
  TIME_OUT=15
  LOOP_COUNT=0
  while [ ${LOOP_COUNT} -le ${TIME_OUT} ]
  do
    pcount=`ps aux|grep ptb-measure-client.pyc|grep -v grep| grep -v tail|wc -l`
    if [ ${pcount} == 1 ]; then
      echo "0"
      break
    else
      let "LOOP_COUNT++"
      sleep 1
    fi
  done
  if [ ${LOOP_COUNT} -eq ${TIME_OUT} ] ; then
    echo "1"
  fi
}

function __internal_stop_status() {
  TIME_OUT=15
  LOOP_COUNT=0
  while [ ${LOOP_COUNT} -le ${TIME_OUT} ]
  do
    pcount=`ps aux|grep ptb-measure-client.pyc|grep -v grep| grep -v tail|wc -l`
    if [ ${pcount} == 0 ]; then
      echo "0"
      break
    else
      let "LOOP_COUNT++"
      sleep 1
    fi
  done
  if [ ${LOOP_COUNT} -eq ${TIME_OUT} ] ; then
    echo "1"
  fi
}

function start() {
  pcount=`ps aux|grep ptb-measure-client.pyc|grep -v grep| grep -v tail|wc -l`
  if [ ${pcount} -ne 0 ]; then
    echo "ptb-measure-client.pyc is already running ..."
    exit 1
  fi
  echo "Starting ptb-measure-client.pyc ..."
  su -c "$DAEMON_BIN"
  INTERNAL_STATUS=`__internal_start_status`
  if [ ${INTERNAL_STATUS} -eq 0 ]; then
    echo "Started ..."
  else
    echo "Failed to Start. Please check the log files ..."
  fi
}

DAEMON_BIN='/opt/ptb-performance-client/ptb-measure-cient.pyc &'


case $1 in
   start)
          start
          ;;
   stop)
          stop
          ;;
   status)
          status
          ;;
   *)
      echo 'Usage: ptb-performance-client-daemon.sh {start|stop|status}'
      exit 1
      ;;
esac

exit 0
