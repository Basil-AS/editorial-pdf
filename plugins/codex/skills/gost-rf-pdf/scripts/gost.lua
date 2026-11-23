local numbering = os.getenv('GOST_NUMBERING')
local project = os.getenv('GOST_PROJECT')
local work = os.getenv('GOST_WORK')
local front = tonumber(os.getenv('GOST_FRONT') or '0')
local draft = os.getenv('GOST_DRAFT') == '1'
local prefix, section, subsection, subsubsection = nil, 0, 0, 0
local counters, global = {}, {}
local ids, refs, objects, headings = {}, {}, {}, {}
local images, toc, landscape = 0, 0, false
local structural = {
  ['введение']=true, ['заключение']=true, ['реферат']=true, ['abstract']=true,
  ['список источников']=true, ['список использованных источников']=true,
  ['список сокращений']=true, ['термины и определения']=true,
  ['перечень сокращений и обозначений']=true, ['список исполнителей']=true
}
local function fail(message) error(message, 0) end
local function raw(s) return pandoc.RawBlock('latex',s) end
local function write(blocks)
  return pandoc.write(pandoc.Pandoc(blocks),'latex'):gsub('%s+$','')
end
local function inline(content)
  return write({pandoc.Plain(content)})
end
local function plain(s)
  local text = inline({pandoc.Str(s)})
  return text:gsub('%-%-%-', '\\textemdash{}'):gsub('%-%-', '\\textendash{}')
end
local function id_for(el)
  local id = el.identifier
  if not id:match('^[a-zA-Z][a-zA-Z0-9_-]*$') then
    fail('Укажите явный ASCII-идентификатор {#id}: '..id)
  end
  if ids[id] then fail('Повтор идентификатора: '..id) end
  ids[id] = true
  return id
end
local function number(kind)
  counters[kind] = (counters[kind] or 0) + 1
  if prefix and (numbering == 'section' or prefix ~= tostring(section)) then
    return prefix..'.'..counters[kind]
  end
  global[kind] = (global[kind] or 0) + 1
  return tostring(global[kind])
end
local function has(el, class) return el.classes:includes(class) end
local function anchor(id) return '\\hypertarget{'..id..'}{}' end
local function heading(el)
  local id = id_for(el)
  local label = pandoc.utils.stringify(el)
  if label:match('%.$') or label:match('^%d+[%. ]') then
    fail('Номер заголовка добавляется автоматически. Уберите точку в конце: '..label)
  end
  local level = el.level
  headings[pandoc.text.lower(label)] = true
  if level > 3 then fail('Поддерживаются три уровня заголовков') end
  if level == 1 then
    subsection, subsubsection, counters = 0, 0, {}
    if has(el,'appendix') then
      prefix = el.attributes.letter
      local permitted = 'АБВГДЕЖИКЛМНПРСТУФХЦШЩЭЮЯABCDEFGHJKLMNPQRSTUVWXYZ'
      if not prefix or utf8.len(prefix) ~= 1 or not permitted:find(prefix,1,true) then
        fail('Приложению нужна допустимая кириллическая буква, например letter="А"')
      end
      if ids['appendix-'..prefix] then fail('Повтор буквы приложения: '..prefix) end
      ids['appendix-'..prefix] = true
      local status = el.attributes.status
      if not status or not ({['обязательное']=true,['рекомендуемое']=true,['справочное']=true})[status] then
        fail('Приложению нужен статус: обязательное, рекомендуемое или справочное')
      end
      label = 'Приложение '..prefix..' ('..status..') '..label
    elseif has(el,'unnumbered') or structural[pandoc.text.lower(label)] then
      prefix = nil
    else
      section = section + 1
      prefix = tostring(section)
      label = prefix..' '..label
    end
  else
    if not prefix then fail('Подраздел вне нумерованной главы или приложения: '..label) end
    if level == 2 then
      subsection = subsection + 1
      subsubsection = 0
      label = prefix..'.'..subsection..' '..label
    else
      if subsection == 0 then fail('Пункт без подраздела: '..label) end
      subsubsection = subsubsection + 1
      label = prefix..'.'..subsection..'.'..subsubsection..' '..label
    end
  end
  local visible = label
  if level == 1 then visible = pandoc.text.upper(label) end
  if has(el,'appendix') then
    visible = 'ПРИЛОЖЕНИЕ '..prefix..'\\\\('..plain(el.attributes.status)..')\\\\'..plain(pandoc.utils.stringify(el))
  else
    visible = plain(visible)
  end
  local command = ({'section','subsection','subsubsection'})[level]
  local start = level == 1 and '\\clearpage' or '\\Needspace{4\\baselineskip}'
  local entry = ''
  if not has(el,'notoc') and level <= 3 then
    entry = '\\addcontentsline{toc}{'..command..'}{'..plain(label)..'}'
  end
  if level == 1 and prefix == tostring(section) then
    command = 'gostnirsection'
    visible = plain(pandoc.text.upper(label))
  end
  return raw(start..'\\phantomsection'..anchor(id)..entry..'\\'..command..'*{'..visible..'}')
end
local function copy_image(src)
  images = images + 1
  local ext = src:match('%.([a-zA-Z]+)$')
  if not ext or not ({pdf=true,png=true,jpg=true,jpeg=true})[ext:lower()]
     or src:match('^/') or src:find('..',1,true) or src:find(string.char(92),1,true)
     or src:find(':',1,true) then
    fail('Используйте локальный PDF, PNG или JPEG: '..src)
  end
  local file = assert(io.open(project..'/'..src,'rb'))
  local data = file:read('*a')
  file:close()
  local target = 'asset-'..images..'.'..ext
  file = assert(io.open(work..'/'..target,'wb'))
  file:write(data)
  file:close()
  return target
end
local function figure(el)
  local id = id_for(el)
  local image = nil
  el:walk({Image=function(img)
    if image then fail('Один рисунок должен содержать один файл') end
    image = img
  end})
  if not image then fail('Нет изображения в рисунке '..id) end
  local cap = pandoc.utils.stringify(pandoc.Pandoc(el.caption.long))
  if cap == '' or cap:match('%.$') then fail('Нужно название рисунка без точки: '..id) end
  objects[id] = true
  local n = number('figure')
  return raw('\\par\\medskip\\noindent\\begin{minipage}{\\linewidth}\\centering\\hyphenpenalty=10000\n'
    ..anchor(id)..'\\GostImage{'..copy_image(image.src)..'}\\par\\smallskip\n'
    ..plain('Рисунок '..n..' – '..cap)..'\\par\\end{minipage}\\par\\medskip')
end
local function table_block(tbl, div)
  local id = id_for(div)
  local cap = pandoc.utils.stringify(pandoc.Pandoc(tbl.caption.long))
  if cap == '' or cap:match('%.$') then fail('Нужно название таблицы без точки: '..id) end
  objects[id] = true
  local n = number('table')
  local count = #tbl.colspecs
  local widths, weight_sum = {}, 0
  for i = 1, count do widths[i] = 0 end
  local function measure(values)
    for _, row in ipairs(values) do
      if #row.cells ~= count then fail('Объединённые ячейки требуют отдельной вёрстки: '..id) end
      for i, cell in ipairs(row.cells) do
        if cell.row_span ~= 1 or cell.col_span ~= 1 then fail('Объединённые ячейки требуют отдельной вёрстки: '..id) end
        -- Match ASCII whitespace explicitly: Lua's locale-aware %s can treat
        -- UTF-8 continuation bytes as spaces and corrupt Cyrillic measurements.
        local text = pandoc.utils.stringify(pandoc.Pandoc(cell.contents)):gsub('[ \t\r\n]+', ' ')
        local chars = utf8.len(text) or #text
        widths[i] = math.max(widths[i], chars)
      end
    end
  end
  measure(tbl.head.rows)
  for _, group in ipairs(tbl.bodies) do
    measure(group.head)
    measure(group.body)
  end
  measure(tbl.foot.rows)
  local table_units = {}
  for i, chars in ipairs(widths) do
    -- Keep short cells tight; cap each column's natural width so prose wraps
    -- before one long cell forces a table back to full-page width.
    local weight = math.min(math.max(chars * 0.52 + 0.7, 2.0), 23.0)
    table_units[i] = weight
    weight_sum = weight_sum + weight
  end
  local caption_label = 'Таблица '..n..' – '..cap
  local natural_units = weight_sum
  local ratios = {}
  for i, weight in ipairs(table_units) do
    ratios[i] = weight / natural_units
  end
  local colspec = '|'
  for i,ratio in ipairs(ratios) do
    local align = ({AlignCenter='\\centering',AlignRight='\\raggedleft'})[tbl.colspecs[i][1]]
      or '\\raggedright'
    colspec = colspec..string.format('>{%s\\arraybackslash}p{\\dimexpr %.8f\\GostTableWidth\\relax}|',align,ratio)
  end
  local function rows(values, header)
    local result = {}
    for _, row in ipairs(values) do
      local cells = {}
      for _, cell in ipairs(row.cells) do
        local value = write(cell.contents)
        cells[#cells+1] = header and '{\\bfseries '..value..'}' or value
      end
      result[#result+1] = table.concat(cells,' & ')..' \\tabularnewline \\hline\n'
    end
    return table.concat(result)
  end
  if #tbl.head.rows == 0 then fail('Таблице нужна головка: '..id) end
  local head, body = rows(tbl.head.rows, true), ''
  for _, group in ipairs(tbl.bodies) do body = body..rows(group.head)..rows(group.body) end
  body = body..rows(tbl.foot.rows)
  if body == '' then fail('Нет данных в таблице: '..id) end
  local function caprow(text, align)
    return '\\multicolumn{'..count..'}{@{}p{\\GostTableWidth}@{}}{\\GostTableCaption{'..align..' '..text..'}} \\\\ \\hline\n'
  end
  return raw('\\begingroup\\GostTableFont\\setlength{\\tabcolsep}{3pt}\\setlength{\\arrayrulewidth}{0.3pt}'
    ..'\\GostColRoom=\\dimexpr\\linewidth-'..(count*2)
    ..'\\tabcolsep-'..(count+1)..'\\arrayrulewidth\\relax\n'
    ..string.format('\\GostTableWidth=\\dimexpr %.4f\\fontdimen6\\font\\relax\n',natural_units)
    ..'\\ifdim\\GostTableWidth>\\GostColRoom \\GostTableWidth=\\GostColRoom \\fi\n'
    ..'\\noindent\\GostTableTitle{'..anchor(id)..plain(caption_label)..'}\n'
    ..'\\begin{longtable}{'..colspec..'}\n'
    ..'\\hline\n'..head..'\\endfirsthead\n'
    ..caprow(plain('Продолжение таблицы '..n),'\\raggedright')
    ..head..'\\endhead\n'..body..'\\end{longtable}\\endgroup')
end
local function blocks(input)
  local result = pandoc.List()
  for index, b in ipairs(input) do
    local out = b
    if b.t == 'Header' then out = heading(b)
    elseif b.t == 'Figure' then out = figure(b)
    elseif b.t == 'Table' then fail('Поместите таблицу в блок ::: {#id .table}')
    elseif b.t == 'RawBlock' then fail('Встроенные HTML и LaTeX блоки не поддерживаются')
    elseif b.t == 'Div' then
      if has(b,'landscape') then
        if landscape or #b.content == 0 then fail('Пустой или вложенный альбомный блок') end
        landscape = true
        result:insert(raw('\\GostLandscapeStart'))
        result:extend(blocks(b.content))
        result:insert(raw('\\GostLandscapeEnd'))
        landscape = false
        out = nil
      elseif has(b,'toc') then
        if landscape or #b.content > 0 or toc > 0 then fail('Маркер навигации должен быть одним пустым книжным блоком') end
        toc = toc + 1
        out = raw('\\GostTOC')
      elseif has(b,'front') then
        if front <= 0 or landscape or index ~= 1 or #b.content > 0 then fail('Укажите --front-pdf с готовыми листами по шаблону') end
        out = raw('\\includepdf[pages=-,pagecommand={\\thispagestyle{gosthidden}},noautoscale]{front.pdf}')
        front = -front
      elseif has(b,'lettered') then
        if #b.content ~= 1 or b.content[1].t ~= 'OrderedList'
          or b.content[1].start ~= 1 or #b.content[1].content > 25 then
          fail('В .lettered требуется список из 1–25 элементов с номера 1')
        end
        local lines = {'\\begin{gostletters}'}
        for _, item in ipairs(b.content[1].content) do
          lines[#lines+1] = '\\item '..write(item)
        end
        lines[#lines+1] = '\\end{gostletters}'
        out = raw(table.concat(lines,'\n'))
      elseif has(b,'table') then
        if #b.content ~= 1 or b.content[1].t ~= 'Table' then fail('В блоке .table должна быть одна таблица') end
        out = table_block(b.content[1],b)
      elseif has(b,'equation') then
        local id = id_for(b)
        objects[id] = true
        local p = b.content[1]
        local m = p and p.content and p.content[1]
        if #b.content ~= 1 or not m or #p.content ~= 1 or m.t ~= 'Math' or m.mathtype ~= 'DisplayMath' then
          fail('В .equation нужна одна формула $$…$$: '..id)
        end
        out = raw('\\par\\begingroup\\abovedisplayskip=21bp\\belowdisplayskip=21bp\\abovedisplayshortskip=21bp\\belowdisplayshortskip=21bp\\begin{equation}'..anchor(id)..m.text..'\\tag{'..number('eq')..'}\\end{equation}\\endgroup')
      elseif has(b,'sources') then
        if #b.content ~= 1 or b.content[1].t ~= 'OrderedList' or b.content[1].start ~= 1 then
          fail('Список источников должен быть одним списком с номера 1')
        end
        local lines = {'\\begin{enumerate}[leftmargin=*,label=\\arabic*.]'}
        for i, item in ipairs(b.content[1].content) do
          local id = 'ref-'..i
          if ids[id] then fail('Повтор идентификатора '..id) end
          ids[id] = true
          objects[id] = true
          lines[#lines+1] = '\\item '..anchor(id)..write(item)
        end
        lines[#lines+1] = '\\end{enumerate}'
        out = raw(table.concat(lines,'\n'))
      else fail('Неизвестный блок: '..table.concat(b.classes,' ')) end
    end
    if out then result:insert(out) end
  end
  return result
end
function Pandoc(doc)
  doc = doc:walk({
    OrderedList=function(el)
      el.delimiter = "OneParen"
      el.style = "Decimal"
      return el
    end,
    Link=function(el)
      local target = el.target:match('^#([A-Za-z][A-Za-z0-9_-]*)$')
      if target then
        refs[target] = (refs[target] or 0) + 1
        return pandoc.RawInline('latex','\\GostRef{'..target..'}{'..inline(el.content)..'}')
      end
      if not el.target:match('^https?://') and not el.target:match('^mailto:') then
        fail('Недопустимая ссылка: '..el.target)
      end
    end,
    RawInline=function() fail('Встроенные HTML и LaTeX фрагменты не поддерживаются') end,
    CodeBlock=function(el)
      if el.text:find('\\end{Verbatim}',1,true) then fail('Недопустимая строка листинга') end
      return raw('\\begin{Verbatim}[fontsize=\\small]\n'..el.text..'\n\\end{Verbatim}')
    end
  })
  doc.blocks = blocks(doc.blocks)
  if front > 0 then fail('Вставьте пустой блок .front в начале документа') end
  if not draft and (front >= 0 or not headings['реферат'] or not headings['введение']
      or not headings['заключение'] or section == 0) then
    fail('Для полного отчёта нужны титул, реферат, введение, основная часть и заключение. Для фрагмента используйте --draft')
  end
  if not draft then
    for id in pairs(objects) do
      if not refs[id] then fail('Нет ссылки на объект: '..id) end
    end
  end
  for target in pairs(refs) do
    if not ids[target] then fail('Не найдена цель ссылки: '..target) end
  end
  return doc
end
