# BPMSort
Flask site to reorganize Spotify Playlist by BPM only for now.

To Configure on your device, everything you need to set is in your .env file.

In your .env file (in the BPMSort directory), make sure to include:

Client ID: From Spotify Dashboard 
  
  formatted: ```CLIENT_ID="your_client_id"```

Client Secret From Spotify Dashboard 
  
  formatted:  ```CLIENT_SECRET="your_client_secret"```

Current URL From your hosting service, can also work as localhost or whatever port you decide to run it from. 
  
  formatted:```CURRENT_URL ="http://localhost:5000/"```

Then, make sure that you run your program using the virtualenv provided, activated from BPMSort using ```source venv/bin/activate```, 
make sure that the (cd) is visible to ensure it's running

Next create a new .env file (in flask_dir directory) and set:
```FLASK_APP="flask_app.py"```

Now you can run the program from flask_dir using ```flask run```

Make sure to save the tree
Tree is saved as 
```tree -I 'venv|*.pyc|__pycache__' > tree.txt```
after every change