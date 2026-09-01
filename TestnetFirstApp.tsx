import { lazy, Suspense, useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { CandlestickSeries, ColorType, createChart, HistogramSeries, LineSeries, type IPriceLine } from 'lightweight-charts'
import { Activity, ArrowUp, Bell, CheckCircle2, CircleDollarSign, Cloud, CloudCog, KeyRound, LockKeyhole, RadioTower, RefreshCw, ShieldCheck, TestTube2 } from 'lucide-react'
import { API_BASE } from './api'

const BinanceDemo = lazy(() => import('./BinanceDemo'))
const CommercialHub = lazy(() => import('./CommercialHub'))
const CloudOpsCenter = lazy(() => import('./CloudOpsCenter'))
const BUILD_COMMIT = import.meta.env.VITE_BUILD_COMMIT

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
type NotificationItem = {id:string;title:string;description:string;kind:'success'|'warning'|'error'|'info'}

const notificationKind = (value:string):NotificationItem['kind'] => {
  if (/error|hata|failed|down|unavailable/i.test(value)) return 'error'
  if (/bek|kontrol|connecting|waiting|locked|kilit/i.test(value)) return 'warning'
  if (/ok|bağlı|active|canlı|kalıcı|hazır/i.test(value)) return 'success'
  return 'info'
}

const healthNotifications = (health:Health|null):NotificationItem[] => {
  if (!health) return []
  return [
    ['api', 'API status', health.status],
    ['database', 'Database status', health.database],
    ['mode', 'Execution mode', health.mode],
    ['testnet', 'Testnet status', health.testnet],
    ['live-guard', 'Live Guard status', health.live_guard],
    ['paper', 'Paper status', health.paper],
    ['evidence', 'Evidence status', health.cloud_evidence],
  ].filter(([, , value]) => Boolean(value)).map(([id,title,description]) => ({
    id,title,description,kind:notificationKind(description),
  }))
}

const format = (value:number) => value.toLocaleString('tr-TR',{maximumFractionDigits:value < 10 ? 5 : 2})

const gateInteraction = (target:View,eventName?:string) => ({
  role:'button' as const,
  tabIndex:0,
  style:{cursor:'pointer'},
  onClick:() => {window.dispatchEvent(new CustomEvent('protrebot-navigate',{detail:target}));if (eventName) window.setTimeout(() => window.dispatchEvent(new Event(eventName)),0)},
  onKeyDown:(event:KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('protrebot-navigate',{detail:target}))
      if (eventName) window.setTimeout(() => window.dispatchEvent(new Event(eventName)),0)
    }
  },
})

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
      layout:{background:{type:ColorType.Solid,color:'#111310'},textColor:'#a49f91'},
      grid:{vertLines:{color:'#272a22'},horzLines:{color:'#272a22'}},
      rightPriceScale:{borderColor:'#3c4034'},timeScale:{borderColor:'#3c4034',timeVisible:true,secondsVisible:false},
      crosshair:{vertLine:{color:'#8b8a52'},horzLine:{color:'#8b8a52'}},
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
  const [credentials,setCredentials] = useState({demoApiKey:'',demoSecretKey:'',liveApiKey:'',liveSecretKey:''})
  const [demoVerification,setDemoVerification] = useState({busy:false,kind:'info',message:''})
  const [notificationsOpen,setNotificationsOpen] = useState(false)
  const [headerHidden,setHeaderHidden] = useState(false)
  const [showBackToTop,setShowBackToTop] = useState(false)
  const notificationRef = useRef<HTMLDivElement>(null)
  const notifications = healthNotifications(health)

  useEffect(() => {
    const navigate = (event:Event) => setView((event as CustomEvent<View>).detail)
    window.addEventListener('protrebot-navigate',navigate)
    return () => window.removeEventListener('protrebot-navigate',navigate)
  },[])

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

  const verifyDemoConnection = async () => {
    const apiKey = credentials.demoApiKey.trim()
    const secretKey = credentials.demoSecretKey.trim()
    if (!apiKey || !secretKey) {
      setDemoVerification({busy:false,kind:'error',message:'Demo API Key ve Secret Key gerekli.'})
      return
    }
    setDemoVerification({busy:true,kind:'info',message:'Demo bağlantısı doğrulanıyor…'})
    try {
      const testResponse = await fetch(`${API_BASE}/exchange-connections/test`,{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({mode:'TESTNET',api_key:apiKey,secret_key:secretKey}),
      })
      const testPayload = await testResponse.json().catch(() => null) as {detail?:unknown;message?:string}|null
      if (!testResponse.ok) throw new Error(typeof testPayload?.detail === 'string' ? testPayload.detail : 'Demo credential doğrulaması başarısız.')

      const saveResponse = await fetch(`${API_BASE}/exchange-connections/save`,{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({mode:'TESTNET',api_key:apiKey,secret_key:secretKey,confirmation:'TESTNET KASAYA KAYDET'}),
      })
      const savePayload = await saveResponse.json().catch(() => null) as {detail?:unknown}|null
      if (!saveResponse.ok) throw new Error(typeof savePayload?.detail === 'string' ? savePayload.detail : 'Demo credential güvenli kasaya kaydedilemedi.')

      const activateResponse = await fetch(`${API_BASE}/exchange-connections/activate`,{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({mode:'TESTNET',confirmation:'TESTNET BAĞLANTIYI AÇ'}),
      })
      const activatePayload = await activateResponse.json().catch(() => null) as {detail?:unknown}|null
      if (!activateResponse.ok) throw new Error(typeof activatePayload?.detail === 'string' ? activatePayload.detail : 'Demo bağlantısı aktifleştirilemedi.')

      const connectResponse = await fetch(`${API_BASE}/binance-demo/connect`,{method:'POST'})
      const connectPayload = await connectResponse.json().catch(() => null) as {detail?:unknown}|null
      if (!connectResponse.ok) throw new Error(typeof connectPayload?.detail === 'string' ? connectPayload.detail : 'Binance Demo hesabı bağlanamadı.')
      setDemoVerification({busy:false,kind:'ok',message:'DEMO CONNECTED · Demo hesabı doğrulandı ve bağlantı aktif.'})
      await refresh()
    } catch (error) {
      setDemoVerification({busy:false,kind:'error',message:error instanceof Error ? error.message : 'Demo bağlantısı doğrulanamadı. Ağ ve vault durumunu kontrol edin.'})
    }
  }

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => void refresh(),60000)
    const openExchangeSettings = () => setView('setup')
    window.addEventListener('protrebot-open-exchange-settings', openExchangeSettings)
    return () => {window.clearInterval(timer);window.removeEventListener('protrebot-open-exchange-settings', openExchangeSettings)}
  },[])

  useEffect(() => {
    if (!notificationsOpen) return
    const closeOnOutsideClick = (event:MouseEvent) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) setNotificationsOpen(false)
    }
    const closeOnEscape = (event:KeyboardEvent) => {if (event.key === 'Escape') setNotificationsOpen(false)}
    document.addEventListener('mousedown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {document.removeEventListener('mousedown', closeOnOutsideClick);document.removeEventListener('keydown', closeOnEscape)}
  },[notificationsOpen])

  useEffect(() => {
    let previousY = window.scrollY
    let ticking = false
    const updateScrollState = () => {
      const currentY = window.scrollY
      const delta = currentY - previousY
      if (currentY <= 12) setHeaderHidden(false)
      else if (Math.abs(delta) >= 8) setHeaderHidden(delta > 0)
      setShowBackToTop(currentY >= 450)
      previousY = currentY
      ticking = false
    }
    const onScroll = () => {
      if (!ticking) {ticking=true;window.requestAnimationFrame(updateScrollState)}
    }
    window.addEventListener('scroll',onScroll,{passive:true})
    return () => window.removeEventListener('scroll',onScroll)
  },[])

  return <main className="v26App">
    <header className={`v26Header ${headerHidden ? 'v26HeaderHidden' : ''}`} data-build-commit={BUILD_COMMIT}>
      <div className="v26Brand"><span>X</span><div><b>PROTREBOT ELITE X</b><small>V27 · CLOUD OPERATIONS / TESTNET-FIRST</small></div></div>
      <div className="v26HeaderSignals">
        <span className="ok"><i/>SUNUCU CANLI</span>
        <span className="ok"><i/>TESTNET ANA MOD</span>
        <span className={health?.cloud_evidence === 'KALICI' ? 'ok' : 'locked'}><Cloud/>{health?.cloud_evidence || 'KANIT BAĞLANIYOR'}</span>
        <span className={health?.live_guard === 'SALT OKUNUR BAĞLI' ? 'ok' : 'locked'}><LockKeyhole/>{health?.live_guard || 'CANLI API BEKLİYOR'}</span>
      </div>
      <div className="v26HeaderActions">
        <button className="v26Refresh" onClick={refresh} disabled={loading}><RefreshCw className={loading ? 'spin' : ''}/>{loading ? 'YENİLENİYOR' : 'YENİLE'}</button>
        <div className="v26Notifications" ref={notificationRef}>
          <button className="v26NotificationButton" type="button" aria-label="Notifications" aria-expanded={notificationsOpen} onClick={() => setNotificationsOpen(open => !open)}><Bell/></button>
          {notificationsOpen && <section className="v26NotificationPanel" role="dialog" aria-label="Notifications">
            <header><div><small>STATUS CENTER</small><h2>Notifications</h2></div><span>{notifications.length}</span></header>
            {notifications.length ? <div className="v26NotificationList">{notifications.map(item => <article key={item.id} className={item.kind}><i><Bell/></i><div><b>{item.title}</b><p>{item.description}</p><small>Current status</small></div></article>)}</div> : <div className="v26NotificationEmpty"><Bell/><b>No notifications</b><p>You're all caught up.<br/>New system notifications will appear here.</p></div>}
          </section>}
        </div>
      </div>
    </header>

    <nav className="v26Nav">
      <button className={view === 'testnet' ? 'active' : ''} onClick={() => setView('testnet')}><TestTube2/><span><b>TESTNET KOMUTA</b><small>Binance Futures Demo · Ana çalışma alanı</small></span></button>
      <button className={view === 'ops' ? 'active' : ''} onClick={() => setView('ops')}><Cloud/><span><b>OPERASYON & KANIT</b><small>Karar, pozisyon ve kalıcı PostgreSQL kaydı</small></span></button>
      <button className={view === 'live' ? 'active liveTab' : ''} onClick={() => setView('live')}><ShieldCheck/><span><b>CANLI HAZIRLIK</b><small>API yoksa kesin kilitli · Gerçek kanal</small></span></button>
      <button className={view === 'setup' ? 'active' : ''} onClick={() => setView('setup')}><CloudCog/><span><b>YAYIN KAPILARI</b><small>Render secret ve geçiş kontrolü</small></span></button>
    </nav>

    <section className="v26ModeBar">
      <div><small>AKTİF ÇALIŞMA ALANI</small><h1>{view === 'testnet' ? 'Binance Futures Demo Merkezi' : view === 'ops' ? 'Bulut Operasyon ve Kanıt Merkezi' : view === 'live' ? 'Gerçek Futures Hazırlık Merkezi' : 'Sunucu ve Anahtar Kapıları'}</h1><p>{view === 'testnet' ? 'Gerçek Binance motoruna en yakın test ortamı; sanal bakiye, gerçek emir akışı ve borsa yanıtları.' : view === 'ops' ? 'Otonom taramanın son kararı, pozisyonlar ve yeniden başlatmaya dayanıklı PostgreSQL kanıt defteri.' : view === 'live' ? 'Şifreli canlı kasa kaydı ve tüm risk kapıları tamamlanana kadar emir gönderimi fail-closed olarak kilitli.' : 'Anahtar değerleri tarayıcıya veya GitHub’a yazılmaz; yalnızca sunucu tarafındaki şifreli kasa veya güvenli geçiş değişkenlerinde tutulur.'}</p></div>
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
        <article className="primary"><TestTube2/><div><small>1 · ŞİMDİ KULLANILACAK</small><h3>Binance Futures Demo</h3><p>Demo API anahtarı yalnızca şifreli vault’a kaydedilir. Gerçek para yoktur; emir, bakiye, pozisyon, Stop ve TP borsa Demo hesabında görünür.</p></div><div className="v26CredentialFields"><label><span>Demo API Key</span><input type="text" value={credentials.demoApiKey} onChange={event => setCredentials(current => ({...current,demoApiKey:event.target.value}))} autoComplete="off" spellCheck={false} placeholder="Demo API anahtarı"/></label><label><span>Demo Secret Key</span><input type="password" value={credentials.demoSecretKey} onChange={event => setCredentials(current => ({...current,demoSecretKey:event.target.value}))} autoComplete="new-password" spellCheck={false} placeholder="Demo Secret anahtarı"/></label><button className="v26DemoVerify" type="button" onClick={verifyDemoConnection} disabled={demoVerification.busy}>{demoVerification.busy ? 'VERIFYING…' : 'VERIFY DEMO CONNECTION'}</button>{demoVerification.message && <small className={`v26DemoVerifyMessage ${demoVerification.kind}`}>{demoVerification.message}</small>}<small>Değerler geçici form state’inden mevcut şifreli vault akışına gönderilir; secret frontend’e geri dönmez.</small></div><strong>{demoVerification.kind === 'ok' ? 'DEMO CONNECTED' : health?.testnet || 'ANAHTAR BEKLİYOR'}</strong></article>
        <article className="future"><LockKeyhole/><div><small>2 · DAHA SONRA</small><h3>Gerçek Binance Futures</h3><p>Canlı altyapı hazırdır. İki secret boş kaldığı sürece bağlantı, izin, kilit ve emir gönderimi açılamaz.</p></div><div className="v26CredentialFields"><label><span>Live API Key</span><input type="text" value={credentials.liveApiKey} onChange={event => setCredentials(current => ({...current,liveApiKey:event.target.value}))} autoComplete="off" spellCheck={false} placeholder="Canlı API anahtarı"/></label><label><span>Live Secret Key</span><input type="password" value={credentials.liveSecretKey} onChange={event => setCredentials(current => ({...current,liveSecretKey:event.target.value}))} autoComplete="new-password" spellCheck={false} placeholder="Canlı Secret anahtarı"/></label><small>Değerler yalnızca bu formun geçici state’inde tutulur.</small></div><strong>{health?.live_guard || 'API BEKLİYOR'}</strong></article>
      </div>
      <div className="v26GateList">
        <article {...gateInteraction('setup')}><span>01</span><div><b>API anahtarları</b><small>Yalnızca Render Environment; GitHub, ekran görüntüsü ve sohbet yasak.</small></div><em>BEKLİYOR</em></article>
        <article {...gateInteraction('live')}><span>02</span><div><b>Salt-okunur hesap testi</b><small>Bakiye, pozisyon modu ve saat farkı doğrulanır; emir oluşmaz.</small></div><em>KİLİTLİ</em></article>
        <article {...gateInteraction('testnet','protrebot-open-demo-certificate')}><span>03</span><div><b>Demo kanıt sertifikası</b><small>30 aktif gün, 100 kapanmış Demo işlem, tatbikat ve drawdown sınırı.</small></div><em>KANIT TOPLAR</em></article>
        <article {...gateInteraction('live')}><span>04</span><div><b>24 saatlik risk izni</b><small>Sunucu belleğinde tutulur; her yeniden başlatmada otomatik iptal olur.</small></div><em>KİLİTLİ</em></article>
        <article {...gateInteraction('live')}><span>05</span><div><b>5 dakikalık son emir kilidi</b><small>Risk politikası onaylı değilse veya herhangi bir kapı eksikse açılamaz.</small></div><em>KİLİTLİ</em></article>
      </div>
      <footer><CheckCircle2/>Altyapı tamamlandıktan sonra ilk aşamada yalnızca Demo secret’larını ekleyeceğiz. Canlı secret’lar boş kalacak.</footer>
    </section>}

    {showBackToTop && <button className="v26BackToTop" type="button" aria-label="Yukarı çık" onClick={() => window.scrollTo({top:0,behavior:'smooth'})}><ArrowUp/></button>}
    <nav className="terminalMobileNav" aria-label="Mobil ana navigasyon"><button className={view === 'testnet' ? 'active' : ''} onClick={() => setView('testnet')}><TestTube2/><span>Dashboard</span></button><button className={view === 'ops' ? 'active' : ''} onClick={() => setView('ops')}><Cloud/><span>Operasyon</span></button><button className={view === 'live' ? 'active' : ''} onClick={() => setView('live')}><ShieldCheck/><span>Canlı</span></button><button className={view === 'setup' ? 'active' : ''} onClick={() => setView('setup')}><CloudCog/><span>Ayarlar</span></button></nav>
    <footer className="v26Footer"><span><RadioTower/>API: <b>{health?.status === 'ok' ? 'BAĞLI' : 'KONTROL EDİLİYOR'}</b></span><span>Veritabanı: <b>{health?.database || '—'}</b></span><span>Kanıt defteri: <b>{health?.cloud_evidence || '—'}</b></span><span>Çalışma modu: <b>TESTNET FIRST</b></span><span>Paper: <b>DEVRE DIŞI</b></span><em>Kâr garantisi yoktur. Testnet sonucu gerçek piyasa sonucunu garanti etmez.</em></footer>
  </main>
}
