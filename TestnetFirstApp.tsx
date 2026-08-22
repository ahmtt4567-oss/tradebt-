import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { CandlestickSeries, ColorType, createChart, HistogramSeries, LineSeries, type IPriceLine } from 'lightweight-charts'
import { Activity, CheckCircle2, CircleDollarSign, Cloud, CloudCog, KeyRound, LockKeyhole, RadioTower, RefreshCw, ShieldCheck, TestTube2 } from 'lucide-react'
import { API_BASE } from './api'

const BinanceDemo = lazy(() => import('./BinanceDemo'))
const CommercialHub = lazy(() => import('./CommercialHub'))
const CloudOpsCenter = lazy(() => import('./CloudOpsCenter'))

type View = 'testnet'|'ops'|'live'|'setup'
type Market = {symbol:string;display:string;price:number;change:number;volume:number}
type Candle = {time:number;open:number;high:number;low:number;close:number;volume:number}
type Point = {time:number;value:number}
type Analysis = {
  direction:'LONG'|'SHORT'|'BEKLE';confidence:number;entry:number;stop_loss:number;tp1:number;tp2:number;tp3:number;
  support:number;resistance:number;trend:string;momentum:string;rsi:number;adx:number;volume_ratio:number;explanation:string;
  series:{ema20:Point[];ema50:Point[];ema200:Point[]}
}
type Health = {status:string;version:string;mode:string;testnet:string;live_guard:string;paper:string;database:string;cloud_evidence:string;web_access:string}

const format = (value:number) => value.toLocaleString('tr-TR',{maximumFractionDigits:value < 10 ? 5 : 2})

function TestnetMarketChart({symbol,interval,onAnalysis}:{symbol:string;interval:string;onAnalysis:(analysis:Analysis|null)=>void}) {
  const host = useRef<HTMLDivElement>(null)
  const [stream,setStream] = useState<'YÜKLENİYOR'|'CANLI'|'HATA'>('YÜKLENİYOR')
  const [updated,setUpdated] = useState('—')

  useEffect(() => {
    if (!host.current) return
    let active = true
    let priceLines:IPriceLine[] = []
    const chart = createChart(host.current,{
      autoSize:true,
      layout:{background:{type:ColorType.Solid,color:'#fffef9'},textColor:'#49614f'},
      grid:{vertLines:{color:'#edf1e8'},horzLines:{color:'#edf1e8'}},
      rightPriceScale:{borderColor:'#d8e3d7'},timeScale:{borderColor:'#d8e3d7',timeVisible:true,secondsVisible:false},
      crosshair:{vertLine:{color:'#70a882'},horzLine:{color:'#70a882'}},
    })
    const candles = chart.addSeries(CandlestickSeries,{upColor:'#0caf62',downColor:'#ef594a',wickUpColor:'#0caf62',wickDownColor:'#ef594a',borderVisible:false})
    const volume = chart.addSeries(HistogramSeries,{priceFormat:{type:'volume'},priceScaleId:''})
    volume.priceScale().applyOptions({scaleMargins:{top:.82,bottom:0}})
    const ema20 = chart.addSeries(LineSeries,{color:'#16a560',lineWidth:2,priceLineVisible:false,lastValueVisible:false,title:'EMA20'})
    const ema50 = chart.addSeries(LineSeries,{color:'#f3a712',lineWidth:2,priceLineVisible:false,lastValueVisible:false,title:'EMA50'})
    const ema200 = chart.addSeries(LineSeries,{color:'#8063d9',lineWidth:2,priceLineVisible:false,lastValueVisible:false,title:'EMA200'})

    const applyAnalysis = (analysis:Analysis) => {
      ema20.setData(analysis.series.ema20.map(point => ({time:point.time as never,value:point.value})))
      ema50.setData(analysis.series.ema50.map(point => ({time:point.time as never,value:point.value})))
      ema200.setData(analysis.series.ema200.map(point => ({time:point.time as never,value:point.value})))
      priceLines.forEach(line => candles.removePriceLine(line))
      const line = (price:number,color:string,title:string,width:1|2|3=2,style=2) => candles.createPriceLine({price,color,lineWidth:width,lineStyle:style,axisLabelVisible:true,title})
      priceLines = [
        line(analysis.entry,'#078b4c',`${analysis.direction} GİRİŞ`,3,0),
        line(analysis.stop_loss,'#ed4f42','STOP',3,0),
        line(analysis.tp1,'#28a657','TP1'),line(analysis.tp2,'#28a657','TP2'),line(analysis.tp3,'#28a657','TP3'),
        line(analysis.support,'#e96b5f','DESTEK',1,3),line(analysis.resistance,'#228d51','DİRENÇ',1,3),
      ]
      onAnalysis(analysis)
    }

    const load = async () => {
      try {
        const [candleResponse,analysisResponse] = await Promise.all([
          fetch(`${API_BASE}/klines/${symbol}?interval=${interval}&limit=500`),
          fetch(`${API_BASE}/analysis/${symbol}?interval=${interval}`),
        ])
        if (!candleResponse.ok || !analysisResponse.ok) throw new Error('Piyasa verisi alınamadı')
        const rows = await candleResponse.json() as Candle[]
        const analysis = await analysisResponse.json() as Analysis
        if (!active) return
        candles.setData(rows.map(row => ({time:row.time as never,open:row.open,high:row.high,low:row.low,close:row.close})))
        volume.setData(rows.map(row => ({time:row.time as never,value:row.volume,color:row.close >= row.open ? 'rgba(24,177,100,.32)' : 'rgba(239,89,74,.28)'})))
        applyAnalysis(analysis)
        chart.timeScale().fitContent()
        setStream('CANLI')
        setUpdated(new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit',second:'2-digit'}))
      } catch {
        if (active) {setStream('HATA');onAnalysis(null)}
      }
    }
    void load()
    const timer = window.setInterval(() => void load(),15000)
    return () => {active=false;window.clearInterval(timer);chart.remove();onAnalysis(null)}
  },[symbol,interval,onAnalysis])

  return <div className="v26ChartShell">
    <div className="v26ChartStatus"><span className={stream === 'CANLI' ? 'live' : stream === 'HATA' ? 'error' : ''}><i/>{stream}</span><em>Binance piyasa verisi · 15 sn yenileme · {updated}</em></div>
    <div className="v26Chart" ref={host}/>
  </div>
}

export default function TestnetFirstApp() {
  const [view,setView] = useState<View>('testnet')
  const [markets,setMarkets] = useState<Market[]>([])
  const [symbol,setSymbol] = useState('BTCUSDT')
  const [interval,setInterval] = useState('15m')
  const [analysis,setAnalysis] = useState<Analysis|null>(null)
  const [health,setHealth] = useState<Health|null>(null)
  const [loading,setLoading] = useState(false)
  const [demoCredentials,setDemoCredentials] = useState({apiKey:'',secretKey:''})

  const refresh = async () => {
    setLoading(true)
    try {
      const [marketResponse,healthResponse] = await Promise.all([
        fetch(`${API_BASE}/markets?limit=12`),
        fetch(`${API_BASE}/health`),
      ])
      if (marketResponse.ok) setMarkets(await marketResponse.json() as Market[])
      if (healthResponse.ok) setHealth(await healthResponse.json() as Health)
    } finally {setLoading(false)}
  }

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => void refresh(),30000)
    const openExchangeSettings = () => setView('setup')
    window.addEventListener('protrebot-open-exchange-settings', openExchangeSettings)
    return () => {window.clearInterval(timer);window.removeEventListener('protrebot-open-exchange-settings', openExchangeSettings)}
  },[])

  return <main className="v26App">
    <header className="v26Header">
      <div className="v26Brand"><span>X</span><div><b>PROTREBOT ELITE X</b><small>V27 · CLOUD OPERATIONS / TESTNET-FIRST</small></div></div>
      <div className="v26HeaderSignals">
        <span className="ok"><i/>SUNUCU CANLI</span>
        <span className="ok"><i/>TESTNET ANA MOD</span>
        <span className={health?.cloud_evidence === 'KALICI' ? 'ok' : 'locked'}><Cloud/>{health?.cloud_evidence || 'KANIT BAĞLANIYOR'}</span>
        <span className={health?.live_guard === 'SALT OKUNUR BAĞLI' ? 'ok' : 'locked'}><LockKeyhole/>{health?.live_guard || 'CANLI API BEKLİYOR'}</span>
      </div>
      <button className="v26Refresh" onClick={refresh} disabled={loading}><RefreshCw className={loading ? 'spin' : ''}/>{loading ? 'YENİLENİYOR' : 'YENİLE'}</button>
    </header>

    <nav className="v26Nav">
      <button className={view === 'testnet' ? 'active' : ''} onClick={() => setView('testnet')}><TestTube2/><span><b>TESTNET KOMUTA</b><small>Binance Futures Demo · Ana çalışma alanı</small></span></button>
      <button className={view === 'ops' ? 'active' : ''} onClick={() => setView('ops')}><Cloud/><span><b>OPERASYON & KANIT</b><small>Karar, pozisyon ve kalıcı PostgreSQL kaydı</small></span></button>
      <button className={view === 'live' ? 'active liveTab' : ''} onClick={() => setView('live')}><ShieldCheck/><span><b>CANLI HAZIRLIK</b><small>API yoksa kesin kilitli · Gerçek kanal</small></span></button>
      <button className={view === 'setup' ? 'active' : ''} onClick={() => setView('setup')}><CloudCog/><span><b>YAYIN KAPILARI</b><small>Render secret ve geçiş kontrolü</small></span></button>
    </nav>

    <section className="v26ModeBar">
      <div><small>AKTİF ÇALIŞMA ALANI</small><h1>{view === 'testnet' ? 'Binance Futures Demo Merkezi' : view === 'ops' ? 'Bulut Operasyon ve Kanıt Merkezi' : view === 'live' ? 'Gerçek Futures Hazırlık Merkezi' : 'Sunucu ve Anahtar Kapıları'}</h1><p>{view === 'testnet' ? 'Gerçek Binance motoruna en yakın test ortamı; sanal bakiye, gerçek emir akışı ve borsa yanıtları.' : view === 'ops' ? 'Otonom taramanın son kararı, pozisyonlar ve yeniden başlatmaya dayanıklı PostgreSQL kanıt defteri.' : view === 'live' ? 'Altyapı hazır; Render canlı API anahtarları eklenene kadar emir gönderimi fiziksel olarak kapalı.' : 'Anahtar değerleri tarayıcıya veya GitHub’a yazılmaz; yalnızca Render Environment kasasında tutulur.'}</p></div>
      <aside><span><CircleDollarSign/>GERÇEK PARA</span><b>{view === 'live' ? 'KİLİTLİ' : '0 USDT'}</b><em>Paper devre dışı</em></aside>
    </section>

    {view === 'testnet' && <>
      <section className="v26MarketBar">
        <div className="v26MarketTitle"><Activity/><span><small>SEÇİLİ TESTNET PAZARI</small><b>{symbol.replace('USDT','/USDT')}</b></span><strong className={analysis?.direction === 'SHORT' ? 'short' : analysis?.direction === 'LONG' ? 'long' : ''}>{analysis?.direction || 'HESAPLANIYOR'} <em>%{analysis?.confidence ?? 0}</em></strong></div>
        <div className="v26MarketPicker">{markets.slice(0,6).map(market => <button key={market.symbol} className={market.symbol === symbol ? 'active' : ''} onClick={() => setSymbol(market.symbol)}><b>{market.display}</b><span>{format(market.price)}</span><em className={market.change >= 0 ? 'up' : 'down'}>{market.change >= 0 ? '+' : ''}{market.change.toFixed(2)}%</em></button>)}</div>
        <div className="v26Intervals">{['1m','5m','15m','1h','4h'].map(item => <button key={item} className={interval === item ? 'active' : ''} onClick={() => setInterval(item)}>{item}</button>)}</div>
      </section>
      <Suspense fallback={<div className="v26Loading"><RefreshCw className="spin"/>Testnet merkezi hazırlanıyor…</div>}>
        <BinanceDemo active symbol={symbol} analysis={analysis} chart={<TestnetMarketChart symbol={symbol} interval={interval} onAnalysis={setAnalysis}/>}/>
      </Suspense>
    </>}

    {view === 'live' && <Suspense fallback={<div className="v26Loading"><RefreshCw className="spin"/>Canlı güvenlik merkezi hazırlanıyor…</div>}><CommercialHub active initialTab="execution"/></Suspense>}

    {view === 'ops' && <Suspense fallback={<div className="v26Loading"><RefreshCw className="spin"/>Bulut operasyon merkezi hazırlanıyor…</div>}><CloudOpsCenter/></Suspense>}

    {view === 'setup' && <section className="v26Setup">
      <header><div><KeyRound/><span><small>SECRETS-ONLY TASARIM</small><h2>İki Ayrı Binance Kanalı</h2></span></div><b><ShieldCheck/>TARAYICIYA ANAHTAR GİRİLMEZ</b></header>
      <div className="v26SetupGrid">
        <article className="primary"><TestTube2/><div><small>1 · ŞİMDİ KULLANILACAK</small><h3>Binance Futures Demo</h3><p>Demo API anahtarı Render’a eklenir. Gerçek para yoktur; emir, bakiye, pozisyon, Stop ve TP borsa Demo hesabında görünür.</p></div><div className="v26DemoCredentials"><label><span>BINANCE_DEMO_API_KEY</span><input type="text" value={demoCredentials.apiKey} onChange={event => setDemoCredentials(current => ({...current,apiKey:event.target.value}))} autoComplete="off" spellCheck={false} placeholder="Demo API anahtarı"/></label><label><span>BINANCE_DEMO_SECRET_KEY</span><input type="password" value={demoCredentials.secretKey} onChange={event => setDemoCredentials(current => ({...current,secretKey:event.target.value}))} autoComplete="new-password" spellCheck={false} placeholder="Demo Secret anahtarı"/></label><small>Değerler yalnızca bu formun geçici state’inde tutulur.</small></div><strong>{health?.testnet || 'ANAHTAR BEKLİYOR'}</strong></article>
        <article className="future"><LockKeyhole/><div><small>2 · DAHA SONRA</small><h3>Gerçek Binance Futures</h3><p>Canlı altyapı hazırdır. İki secret boş kaldığı sürece bağlantı, izin, kilit ve emir gönderimi açılamaz.</p></div><ul><li><code>BINANCE_LIVE_API_KEY</code></li><li><code>BINANCE_LIVE_SECRET_KEY</code></li></ul><strong>{health?.live_guard || 'API BEKLİYOR'}</strong></article>
      </div>
      <div className="v26GateList">
        <article><span>01</span><div><b>API anahtarları</b><small>Yalnızca Render Environment; GitHub, ekran görüntüsü ve sohbet yasak.</small></div><em>BEKLİYOR</em></article>
        <article><span>02</span><div><b>Salt-okunur hesap testi</b><small>Bakiye, pozisyon modu ve saat farkı doğrulanır; emir oluşmaz.</small></div><em>KİLİTLİ</em></article>
        <article><span>03</span><div><b>Demo kanıt sertifikası</b><small>30 aktif gün, 100 kapanmış Demo işlem, tatbikat ve drawdown sınırı.</small></div><em>KANIT TOPLAR</em></article>
        <article><span>04</span><div><b>24 saatlik risk izni</b><small>Sunucu belleğinde tutulur; her yeniden başlatmada otomatik iptal olur.</small></div><em>KİLİTLİ</em></article>
        <article><span>05</span><div><b>5 dakikalık son emir kilidi</b><small>Risk politikası onaylı değilse veya herhangi bir kapı eksikse açılamaz.</small></div><em>KİLİTLİ</em></article>
      </div>
      <footer><CheckCircle2/>Altyapı tamamlandıktan sonra ilk aşamada yalnızca Demo secret’larını ekleyeceğiz. Canlı secret’lar boş kalacak.</footer>
    </section>}

    <footer className="v26Footer"><span><RadioTower/>API: <b>{health?.status === 'ok' ? 'BAĞLI' : 'KONTROL EDİLİYOR'}</b></span><span>Veritabanı: <b>{health?.database || '—'}</b></span><span>Kanıt defteri: <b>{health?.cloud_evidence || '—'}</b></span><span>Çalışma modu: <b>TESTNET FIRST</b></span><span>Paper: <b>DEVRE DIŞI</b></span><em>Kâr garantisi yoktur. Testnet sonucu gerçek piyasa sonucunu garanti etmez.</em></footer>
  </main>
}
