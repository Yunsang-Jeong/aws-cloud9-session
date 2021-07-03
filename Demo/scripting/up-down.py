import random

x = random.randint(1,100)

count = 1
while True:
    i = input('Guess a number: ')
    guess = int(i)
    if guess < x:
        print('[Try {}] {} is too small'.format(count, guess))
        count+=1
    elif guess > x:
        print('[Try {}] {} is too big'.format(count, guess))
        count+=1
    else:
        break
    
print('You did it in try {}!'.format(count))