#!/bin/bash
# Отпечаток КП «Авто» для сайта: файлы сделок, углы табличек и фото сделок (имя и время изменения)
A=/home/sergei/auto-china
{ cat $A/kp_v3/deals/*.py $A/kp_v3/plates_kp.json; stat -c '%n %Y' $A/assets/*/car*.jpg; } 2>/dev/null | md5sum | cut -c1-32
