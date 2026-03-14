from flask import Flask, render_template, request
import random

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def game():
    result = ""
    computer_choice = ""
    if request.method == "POST":
        player_choice = request.form["choice"]
        computer_choice = random.choice(["stone", "paper", "sissor"])
        result = get_result(player_choice, computer_choice)
    return render_template("index.html", result=result, computer_choice=computer_choice)

def get_result(player, computer):
    if player == computer:
        return "Match Draw!"
    elif (player == "stone" and computer == "sissor") or \
         (player == "paper" and computer == "stone") or \
         (player == "sissor" and computer == "paper"):
        return "You win!"
    else:
        return "Computer wins!"

if __name__ == "__main__":
    app.run(debug=True)
