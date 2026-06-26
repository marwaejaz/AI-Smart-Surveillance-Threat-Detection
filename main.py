from dashboard import LoginScreen, SurveillanceDashboard

def launch_dashboard():
    app = SurveillanceDashboard()
    app.run()

if __name__ == "__main__":
    login = LoginScreen(on_success=launch_dashboard)
    login.run()
