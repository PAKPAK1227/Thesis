import requests

post_id = input("Enter a post number (1-100): ")

url = "https://jsonplaceholder.typicode.com/posts"

params = {
    "id": post_id
}

response = requests.get(url, params=params)

data = response.json() #this returns a list that contains dictionaries

print(data)

# print(data.keys()) #greatest way to inspect the keys of a api call that you have no idea about
# remember nested data exists in nesting dictionaries as using a list of dictionaries as a value in a key-value pair
# relationship