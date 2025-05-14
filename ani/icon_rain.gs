'reinit'
'set background 1'
'c'

'sdfopen /data/C.shaoyu/hackathon/icon/PT1H_inst/pr.nc'
'sdfopen /data/C.shaoyu/hackathon/nicam/2dbc/orog.nc'
file='/data/C.shaoyu/ats/obs/shao_ATdays_2020_2020_icon.txt'


topocmap='250 3000 250 -gxout shaded -kind white->(100,100,100)'
raincmap='-levs 2 5 10 15 25 -gxout grfill -kind (255,255,255,0)-(0)->(84,104,245)->(11,191,38)->(242,226,5)->(242,5,5)->(204,7,204)'

date='18JUN2020'
while (1)
  res = read(file)
  line1 = sublin(res,1)
  line2 = sublin(res,2)
  rc1 = subwrd(line1,1)
  if (rc1); break; endif
  date = subwrd(line2,1)
  say date

  'set time 'date
  'q dim'
  line=sublin(result,5)
  tcenter=subwrd(line,9)
  t0=tcenter-8
  t1=tcenter+15
  
*'set time 16:30Z17JUN2020 15:30Z18JUN2020'
*  'set lon 119 123'
*  'set lat 21.5 26'
  'set lon 119.7 122.3'
  'set lat 21.8 25.5'

* figure setting 
  'c'
  'set parea 2.58333 8.41667 0.8 7.55'
  'set xlopts 1 10 0.2'
  'set ylopts 1 10 0.2'
  'set grads off'
  'set timelab off'
  'set ylint 1'
  'set xlint 1'
  'set mpdset hires'
  
  'color 'topocmap
  'd orog.2(t=1,z=1)'
  'xcbar 8.5 8.8 0.8 7.55'

  'color 'raincmap
  'd ave(pr.1,t='t0',t='t1')*3600*24'
  'xcbar 7.8 8.1 0.8 7.55'

  'set string 1 bl 10 0'
  'set strsiz 0.25'
  'draw string 3.6 7.7 ICON'

  'set string 1 br 10 0'
  'set strsiz 0.2'
  'draw string 8.8 7.7 'date
  'draw string 8.8 8 daily [mm`a `nd`a-1`n]'

  '! mkdir -p ./fig/icon/daily/'
  'gxprint ./fig/icon/daily/ats_'date'.png x1100 y850'
  
  it=1
  while(it<=24)
  'c'
  'set t 't0+it
  'q time'
  say result
  'set xlopts 1 10 0.2'
  'set ylopts 1 10 0.2'
  'set grads off'
  'set timelab off'
  'set ylint 1'
  'set xlint 1'
  'set mpdset hires'
  
*  'color 0 3000 500 -gxout shaded -kind white->(150,150,150)'
  'color 'topocmap
  'd orog.2(t=1,z=1)'
  'xcbar 8.5 8.8 0.8 7.55'
  
*  'color -levs 1 3 5 7 10 15 20 -gxout grfill -kind (255,255,255,0)->grainbow'
  'color 'raincmap
  'd pr.1*3600'
  'xcbar 7.8 8.1 0.8 7.55'

  tstr=math_format('%02.0f', it)
  'set string 1 bl 10 0'
  'set strsiz 0.25'
  'draw string 3.6 7.7 ICON'

  'set string 1 br 10 0'
  'set strsiz 0.2'
  'draw string 8.8 7.7 'date
  'draw string 8.8 8 'tstr'LT [mm`a `nhr`a-1`n]'
  
  '! mkdir -p ./fig/icon/'date
  'gxprint ./fig/icon/'date'/ats_'tstr'.png x1100 y850'
  
  it=it+1
  endwhile

*read file
endwhile




