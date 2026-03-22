import bcrypt

password = "PerkupCafe321"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

print(hashed.decode('utf-8'))