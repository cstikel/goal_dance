import RPi.GPIO as GPIO
import requests
from datetime import date, datetime, timezone
import time

GPIO.setwarnings(False)

LedPin = 17
servoPIN = 14

team_id = 14
team_abr = 'tbl'


def setup():
    # Set the GPIO modes to BCM Numbering
    GPIO.setmode(GPIO.BCM)
    # Set LedPin's mode to output,and initial level to High(3.3v)
    GPIO.setup(LedPin, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(servoPIN, GPIO.OUT)


def SetAngle(angle):
	duty = angle / 18 + 2
	GPIO.output(servoPIN, True)
	p.ChangeDutyCycle(duty)
	time.sleep(0.5)
	GPIO.output(servoPIN, False)
	p.ChangeDutyCycle(0)


def goallight():
    SetAngle(0)
    time.sleep(0.5)
    SetAngle(180)
    x = 1
    while x<15:
        print ('GOOOOOAAAALLL')
        # Turn on LED
        GPIO.output(LedPin, GPIO.LOW)
        time.sleep(0.5)
        print ('THE BOLTS SCOOOORRRREEEEEE!!!!')
        # Turn off LED
        GPIO.output(LedPin, GPIO.HIGH)
        time.sleep(0.5)
        x += 1

    SetAngle(0)

# Define a destroy function for clean up everything after the script finished
def destroy():
    # Turn off LED
    GPIO.output(LedPin, GPIO.HIGH)
    # Release resource
    SetAngle(0)
    GPIO.cleanup()                   


def datetime_from_utc_to_local(utc_datetime):
    '''Function that converts the utc time in the NHL api to the local timezone'''
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    
    return utc_datetime + offset


def update_schedule(team_abr, team_id):
    ''' 
    Takes a team ID and returns a DF of their schedule with the important pieces of informations.
    '''
    df_dict = {"date": [],
            "game_id" : [],
            "game_date_time" : [],
            "home_away" : []}
    
    #gets the season json from NHL
    season_json = requests.get(f"https://api-web.nhle.com/v1/club-schedule-season/{team_abr}/now")
    season_json = season_json.json()
    
    #turns the json into a df with all the impoertant pieces of information
    for i in season_json['games']:
        df_dict["date"].append(datetime.strptime(i['gameDate'], "%Y-%m-%d").date())
        df_dict["game_id"].append(i["id"])
        game_time = datetime.strptime(i['startTimeUTC'], "%Y-%m-%dT%H:%M:%SZ")
        df_dict["game_date_time"].append(datetime_from_utc_to_local(game_time))
        
        if i['awayTeam']['id'] == team_id:
            df_dict["home_away"].append('awayTeam')
            #df_dict["bad_guys"].append(game["teams"]["home"]["team"]["name"])
        else:
            df_dict["home_away"].append('homeTeam')
            #df_dict["bad_guys"].append(game["teams"]["away"]["team"]["name"])

    
    return df_dict


def check_game_day(schedule):
    '''Function to check if there is a game today'''
    if date.today() in schedule['date']: 
        game_today = True
    else:
        game_today = False
        
    return game_today

def game_info(schedule_dict):
    ''' Function that returns all the game info to be passed into the game function'''
    #filter to row in schedule for the game
    dict_ind = schedule_dict['date'].index(date.today())
    game_id = schedule_dict['game_id'][dict_ind]
    home_away = schedule_dict['home_away'][dict_ind]
    g_time = schedule_dict['game_date_time'][dict_ind]
    
    return game_id, home_away, g_time 

def get_game_json(game_id):
    ''' Function that returns the boxscore json from NHL API'''
    game_json = requests.get(f'https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore')
    game_json = game_json.json()
    
    return game_json


def get_goal_count(game_json, home_away):
    '''Function that get the current goals for the identified team'''
    goals = game_json[home_away]['score']
    
    return goals

def get_time_to_game(g_time):
    '''Function that gets how much time until puck drop'''
    now  = datetime.now().replace(tzinfo=None)
            
    duration = g_time - now
    duration_in_s = duration.total_seconds()
    duration_in_m = duration_in_s / 60
    duration_in_h = duration_in_m / 60
        
    return duration_in_s, duration_in_m, duration_in_h
           
            
def game_over(game_json):
    '''Function that returns True if the game is over'''
    if game_json["gameState"] == "OFF":
        status = True
    else:
        status = False
        
    return status

def main():

    #SetAngle(0)
    while True:
        schedule = update_schedule(team_abr, team_id)
        while check_game_day( schedule=schedule):
            print("Game Day")
            game_id, home_away, g_time = game_info(schedule)
            duration_in_s, duration_in_m, duration_in_h = get_time_to_game(g_time)
            print(f"Game is at {g_time} .")
            print(f"{duration_in_m} minutes until puck drop, or {duration_in_h} hours.")


            current_goals = 0
            
            print("Game script is running!")
            #goallight()
            #SetAngle(0)

            while duration_in_m <= 1:
                try:
                    game_json = get_game_json(game_id)
                    #I think the current goal needs to move outside of the while loop
                    #current_goals = get_goal_count(game_json, home_away=home_away)
                    goals = get_goal_count(game_json, home_away=home_away)
                    if current_goals != goals :
                        goallight()
                        current_goals = goals
                        print('Goal celly is done.')
                        SetAngle(0)
                    else:
                        if game_over(game_json):
                            break
                        else:
                            print(game_json['clock']['timeRemaining'], " - Scores the same.", current_goals)
                            time.sleep(4)
                    
                except:
                    time.sleep(60)
            else:
                print(f"I am going to sleep until 1 minute before puck drop")
                time.sleep(duration_in_s - 60)
        
        print("Not game day, going to sleep for a few hours")                   
        time.sleep(43200)

       

if __name__ == '__main__':
    setup() 
    p = GPIO.PWM(servoPIN, 50) 
    p.start(2)
    try:
        main()
    # When 'Ctrl+C' is pressed, the program destroy() will be  executed.
    except KeyboardInterrupt:
        destroy()

