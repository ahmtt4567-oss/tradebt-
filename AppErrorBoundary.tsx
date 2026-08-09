import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children:ReactNode }
type State = { failed:boolean; message:string }

export default class AppErrorBoundary extends Component<Props,State> {
  state:State = {failed:false,message:''}

  static getDerivedStateFromError(error:unknown):State {
    return {
      failed:true,
      message:error instanceof Error ? error.message : 'Beklenmeyen bir ekran hatası oluştu.',
    }
  }

  componentDidCatch(error:unknown, info:ErrorInfo) {
    console.error('ProTreBot güvenli ekran koruması', error, info.componentStack)
  }

  private recover = () => {
    this.setState({failed:false,message:''})
    window.location.reload()
  }

  render() {
    if (!this.state.failed) return this.props.children
    return <main className="appRecoveryShell" role="alert">
      <section className="appRecoveryCard">
        <span className="appRecoveryLogo">X</span>
        <small>GÜVENLİ EKRAN KORUMASI</small>
        <h1>Panel kapatılmadı</h1>
        <p>Geçici veya eksik bir veri yakalandı. Demo işlem gerçek emir değildir; mevcut kayıt korunur.</p>
        <div><b>Tekrar yüklemek güvenlidir</b><span>{this.state.message || 'Veri yeniden istenecek.'}</span></div>
        <button type="button" onClick={this.recover}>PANELİ GÜVENLİ YENİLE</button>
      </section>
    </main>
  }
}
