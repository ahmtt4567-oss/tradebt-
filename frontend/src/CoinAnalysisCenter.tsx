import { type ReactNode, useEffect, useMemo, useState } from 'react'
import { BarChart3, ChevronDown, ChevronUp, Filter, RefreshCw, Search } from 'lucide-react'
import { API_BASE } from './api'

type AnalysisRow = {
  symbol:string; display:string; price:number; change:number; volume:number; volume_ratio:number
  rsi:number; ema20:number; ema50:number; ema200:number; trend:string; direction:'LONG'|'SHORT'|'BEKLE'
  confidence:number; entry:number; stop_loss:number; tp1:number; tp2:number; tp3:number; support:number; resistance:number
}
type Analysis = { direction:'LONG'|'SHORT'|'BEKLE'; confidence:number; entry:number; stop_loss:number; tp1:number; tp2:number; tp3:number; support:number; resistance:number; trend:string; rsi:number; series:{ema20:{time:number;value:number}[];ema50:{time:number;value:number}[];ema200:{time:number;value:number}[]} }
const intervals = ['1m','5m','15m','30m','1h','4h','1d']
const fmt = (value?:number) => value === undefined || !Number.isFinite(value) ? '—' : value.toLocaleString('tr-TR',{maximumFractionDigits:value < 10 ? 4 : 2})
const signal = (row:AnalysisRow) => row.confidence >= 80 ? `GÜÇLÜ ${row.direction}` : row.direction

function Metric({label,value}:{label:string;value:ReactNode}) { return <span><small>{label}</small><b>{value}</b></span> }

export default function CoinAnalysisCenter({interval,onIntervalChange,chart}:{interval:string;onIntervalChange:(value:string)=>void;chart:(symbol:string,interval:string)=>ReactNode}) {
  const [rows,setRows] = useState<AnalysisRow[]>([])
  const [selected,setSelected] = useState('BTCUSDT')
  const [query,setQuery] = useState('')
  const [filters,setFilters] = useState<string[]>([])
  const [sort,setSort] = useState<keyof AnalysisRow>('volume')
  const [ascending,setAscending] = useState(false)
  const [loading,setLoading] = useState(false)
  const [error,setError] = useState('')
  const [mobileFilters,setMobileFilters] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/analysis-universe?interval=${interval}&limit=120`)
      const payload = await response.json() as {results?:AnalysisRow[];detail?:string}
      if (!response.ok) throw new Error(payload.detail || 'Coin analiz verisi alınamadı.')
      setRows(payload.results || []); setError('')
      if (payload.results?.length && !payload.results.some(row => row.symbol === selected)) setSelected(payload.results[0].symbol)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Coin analiz verisi alınamadı.') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load(); const timer = window.setInterval(() => void load(),60000); return () => window.clearInterval(timer) },[interval])

  const matchesFilter = (row:AnalysisRow, current:string) => current === 'USDT' || current === row.direction ||
    (current === 'STRONG_LONG' && row.direction === 'LONG' && row.confidence >= 80) ||
    (current === 'STRONG_SHORT' && row.direction === 'SHORT' && row.confidence >= 80) ||
    (current === 'EMA20_50' && row.ema20 > row.ema50) || (current === 'EMA50_200' && row.ema50 > row.ema200) ||
    (current === 'PRICE20' && row.price > row.ema20) || (current === 'PRICE50' && row.price > row.ema50) ||
    (current === 'PRICE200' && row.price > row.ema200) || (current === 'HIGH_VOLUME' && row.volume_ratio >= 1.25) ||
    (current === 'VOLUME_UP' && row.volume_ratio >= 1.05) || (current === 'RSI_HIGH' && row.rsi >= 60) ||
    (current === 'RSI_LOW' && row.rsi <= 40) || (current === 'TREND_BULL' && row.trend.toUpperCase().includes('YÜKSEL')) ||
    (current === 'TREND_BEAR' && row.trend.toUpperCase().includes('DÜŞ')) ||
    (current === 'CHANGE_UP' && row.change >= 0) || (current === 'CHANGE_DOWN' && row.change < 0) ||
    (current === 'STOP_CLOSE' && Math.abs(row.price - row.stop_loss) / row.price <= .02) ||
    (current === 'TP_CLOSE' && Math.min(Math.abs(row.price - row.tp1),Math.abs(row.price - row.tp2),Math.abs(row.price - row.tp3)) / row.price <= .02)
  const visible = useMemo(() => rows.filter(row => row.display.toUpperCase().includes(query.toUpperCase()) && filters.every(current => matchesFilter(row,current))).sort((left,right) => { const a = left[sort]; const b = right[sort]; return (a < b ? -1 : a > b ? 1 : 0) * (ascending ? 1 : -1) }),[rows,query,filters,sort,ascending])
  const active = rows.find(row => row.symbol === selected) || visible[0]
  const chooseSort = (key:keyof AnalysisRow) => { if (sort === key) setAscending(value => !value); else { setSort(key); setAscending(false) } }
  const sortIcon = (key:keyof AnalysisRow) => sort === key ? ascending ? <ChevronUp/> : <ChevronDown/> : null
  const filterOptions = [['ALL','TÜM COINLER'],['USDT','SADECE USDT'],['LONG','LONG'],['SHORT','SHORT'],['BEKLE','NÖTR'],['STRONG_LONG','GÜÇLÜ LONG'],['STRONG_SHORT','GÜÇLÜ SHORT'],['EMA20_50','EMA20 > EMA50'],['EMA50_200','EMA50 > EMA200'],['PRICE20','FİYAT EMA20 ÜSTÜ'],['PRICE50','FİYAT EMA50 ÜSTÜ'],['PRICE200','FİYAT EMA200 ÜSTÜ'],['STOP_CLOSE','STOP’A YAKIN'],['TP_CLOSE','TP’YE YAKIN'],['HIGH_VOLUME','YÜKSEK HACİM'],['VOLUME_UP','HACİM ARTIŞI'],['RSI_HIGH','RSI YÜKSEK'],['RSI_LOW','RSI DÜŞÜK'],['TREND_BULL','TREND BULLISH'],['TREND_BEAR','TREND BEARISH'],['CHANGE_UP','DEĞİŞİM POZİTİF'],['CHANGE_DOWN','DEĞİŞİM NEGATİF']]
  const toggleFilter = (value:string) => setFilters(current => value === 'ALL' ? [] : current.includes(value) ? current.filter(item => item !== value) : [...current,value])
  const cells = (row:AnalysisRow) => [<b>{row.display}</b>,fmt(row.price),<em className={row.change >= 0 ? 'positive' : 'negative'}>{row.change >= 0 ? '+' : ''}{fmt(row.change)}%</em>,fmt(row.volume),fmt(row.rsi),fmt(row.ema20),fmt(row.ema50),fmt(row.ema200),row.trend,<strong className={row.direction === 'LONG' ? 'positive' : row.direction === 'SHORT' ? 'negative' : ''}>{signal(row)}</strong>,fmt(row.entry),fmt(row.stop_loss),fmt(row.tp1),fmt(row.tp2),fmt(row.tp3)]

  return <section className="coinAnalysisCenter">
    <header className="coinAnalysisHeader"><div><span><BarChart3/> GERÇEK BİNANCE VERİSİ · 60 SN CACHE</span><h2>Coin Analiz Merkezi</h2><p>EMA, RSI, seviye ve sinyal değerleri seçilen timeframe mumlarından hesaplanır.</p></div><button type="button" onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? 'spin' : ''}/>{loading ? 'YÜKLENİYOR' : 'YENİLE'}</button></header>
    <div className="coinAnalysisToolbar"><label><Search/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Coin ara…"/></label><button className="mobileFilterButton" type="button" onClick={() => setMobileFilters(value => !value)}><Filter/>FİLTRELER{filters.length ? ` · ${filters.length}` : ''}</button><div className={mobileFilters ? 'coinFilters open' : 'coinFilters'}>{filterOptions.map(([value,label]) => <button type="button" key={value} className={(value === 'ALL' ? filters.length === 0 : filters.includes(value)) ? 'active' : ''} onClick={() => toggleFilter(value)}>{label}</button>)}</div></div>
    <div className="coinIntervals">{intervals.map(item => <button type="button" key={item} className={interval === item ? 'active' : ''} onClick={() => onIntervalChange(item)}>{item}</button>)}</div>
    {error && <div className="coinAnalysisError">{error}</div>}
    <div className="coinAnalysisLayout">
      <div className="coinTablePanel"><div className="coinTableMeta"><b>{visible.length} coin</b><span>Dinamik USDT evreni · {interval}</span></div><div className="coinTableScroll"><table><thead><tr>{[['symbol','COIN'],['price','FİYAT'],['change','24H %'],['volume','HACİM'],['rsi','RSI'],['ema20','EMA20'],['ema50','EMA50'],['ema200','EMA200'],['trend','TREND'],['direction','SİNYAL'],['entry','GİRİŞ'],['stop_loss','STOP'],['tp1','TP1'],['tp2','TP2'],['tp3','TP3']].map(([key,label]) => <th key={key}><button type="button" onClick={() => chooseSort(key as keyof AnalysisRow)}>{label}{sortIcon(key as keyof AnalysisRow)}</button></th>)}</tr></thead><tbody>{visible.map(row => <tr key={row.symbol} className={row.symbol === selected ? 'selected' : ''} onClick={() => setSelected(row.symbol)}>{cells(row).map((cell,index) => <td key={index}>{cell}</td>)}</tr>)}</tbody></table>{!loading && !visible.length && <div className="coinEmpty">Filtreye uyan canlı coin bulunamadı.</div>}{loading && <div className="coinEmpty">Analiz evreni hazırlanıyor…</div>}</div></div>
      <aside className="coinDetailPanel">{active ? <><div className="coinDetailTitle"><div><span>SEÇİLİ COIN · CANLI ANALİZ</span><h3>{active.display}</h3></div><strong className={active.direction === 'LONG' ? 'positive' : active.direction === 'SHORT' ? 'negative' : ''}>{signal(active)}</strong></div><div className="coinDetailMetrics"><Metric label="CANLI FİYAT" value={fmt(active.price)}/><Metric label="24H DEĞİŞİM" value={<em className={active.change >= 0 ? 'positive' : 'negative'}>{active.change >= 0 ? '+' : ''}{fmt(active.change)}%</em>}/><Metric label="HACİM" value={fmt(active.volume)}/><Metric label="RSI" value={fmt(active.rsi)}/></div><div className="coinDetailLevels"><Metric label="TREND" value={active.trend}/><Metric label="EMA20" value={fmt(active.ema20)}/><Metric label="EMA50" value={fmt(active.ema50)}/><Metric label="EMA200" value={fmt(active.ema200)}/><Metric label="GİRİŞ" value={fmt(active.entry)}/><Metric label="STOP" value={fmt(active.stop_loss)}/><Metric label="TP1" value={fmt(active.tp1)}/><Metric label="TP2" value={fmt(active.tp2)}/><Metric label="TP3" value={fmt(active.tp3)}/><Metric label="DESTEK" value={fmt(active.support)}/><Metric label="DİRENÇ" value={fmt(active.resistance)}/></div><div className="coinDetailChart">{chart(active.symbol,interval)}</div></> : <div className="coinEmpty">Canlı analiz seçilince detay burada açılır.</div>}</aside>
    </div>
    <div className="coinMobileCards">{visible.map(row => <button type="button" className={row.symbol === selected ? 'active' : ''} key={row.symbol} onClick={() => setSelected(row.symbol)}><b>{row.display}</b><span>{fmt(row.price)}</span><em className={row.change >= 0 ? 'positive' : 'negative'}>{row.change >= 0 ? '+' : ''}{fmt(row.change)}%</em><strong className={row.direction === 'LONG' ? 'positive' : row.direction === 'SHORT' ? 'negative' : ''}>{signal(row)}</strong></button>)}</div>
  </section>
}
