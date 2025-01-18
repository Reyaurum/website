import os
import time

os.system("cls")

table = []
keyedAlphabet = ["K","R","Y","P","T","O","S","A","B","C","D","E","F","G","H","I","J","L","M","N","Q","U","V","W","X","Z","k","r","y","p","t","o","s","a","b","c","d","e","f","g","h","i","j","l","m","n","q","u","v","w","x","z"," ", ",", ".", "/", '"', "'"]

for x in range(len(keyedAlphabet)):
    table.append(keyedAlphabet[x : x + len(keyedAlphabet)])
    table[x] += (keyedAlphabet[0 : x])

def viewTable():
    for x in table:
        print(x)
    print("\n")

def encrypt():
    encryptedPhrase = ""
    currentKeywordLetterIndex = 0

    os.system("CLS")

    originalPhrase = input("ORIGINAL PHRASE: ")
    keyword = input("KEYWORD: ")

    for currentOriginalLetter in originalPhrase:
        currentKeywordLetter = keyword[currentKeywordLetterIndex]
        currentKeywordLetterPos = table[0].index(currentKeywordLetter)
        currentOriginalLetterPos = table[0].index(currentOriginalLetter)

        encryptedLetter = table[currentKeywordLetterPos][currentOriginalLetterPos]

        encryptedPhrase += encryptedLetter

        if currentKeywordLetterIndex < len(keyword) - 1:
            currentKeywordLetterIndex += 1
        else:
            currentKeywordLetterIndex = 0

    print("ENCRYPTED PHRASE:", encryptedPhrase, "\n")

def decrypt():
    decryptedPhrase = ""
    currentKeywordLetterIndex = 0

    os.system("CLS")

    encryptedPhrase = input("ENCRYPTED PHRASE: ")
    keyword = input("KEYWORD: ")

    for currentEncryptedLetter in encryptedPhrase:
        currentKeywordLetter = keyword[currentKeywordLetterIndex]
        currentKeywordLetterPos = table[0].index(currentKeywordLetter)
        currentEncryptedLetterPos = table[currentKeywordLetterPos].index(currentEncryptedLetter)

        decryptedLetter = table[0][currentEncryptedLetterPos]

        decryptedPhrase += decryptedLetter

        if currentKeywordLetterIndex < len(keyword) - 1:
            currentKeywordLetterIndex += 1
        else:
            currentKeywordLetterIndex = 0

    print("DECRYPTED PHRASE:", decryptedPhrase, "\n")

def chooseState():
    choice = "0"
    print("[1] Encrypt")
    print("[2] Decrypt")

    while choice != "1" or choice != "2":
        choice = str(input())
        if (choice == "1"):
            encrypt()
            chooseState()
        
        elif (choice == "2"):
            decrypt()
            chooseState()

viewTable()
chooseState()