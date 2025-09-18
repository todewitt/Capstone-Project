from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/account")
def account():
    return render_template("account.html")

@app.route("/log-out")
def logout():
    return render_template("log-out.html")

@app.route("/order-history")
def orderHistory():
    return render_template("order-history.html")

@app.route("/withdraw-deposit")
def withdrawDeposit():
    return render_template("withdraw-deposit.html")




if __name__ == "__main__":
    app.run(debug=True)
    