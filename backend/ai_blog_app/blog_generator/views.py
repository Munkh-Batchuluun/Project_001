from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from pytube import YouTube
from django.conf import settings
import os
import assemblyai as aai
import openai
import re
from .models import BlogPost

# Create your views here.
@login_required
def index (req):
    return render(req, 'index.html')

@csrf_exempt
def generate_blog(req):
    if req.method == 'POST':
        try:
            data = json.loads(req.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)
        
        # get yt title
        title = yt_title(yt_link)

        # get trascript
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': "Failed to get transcript"}, status=500)

        # use OpenAI to generate blog
        blog_content = generate_blog_from_transcription(transcription)
        if not transcription:
            return JsonResponse({'error': "Failed to generate article"}, status=500)

        # save blog article to database
        new_blog_article = BlogPost.objects.create(
            user = req.user,
            youtube_title = title,
            youtube_link = yt_link,
            generated_content = blog_content
        )
        new_blog_article.save()

        # return blog article as a response
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({ 'error': 'Invalid request method'}, status=405)

def yt_title (link):
    yt = YouTube(link)
    title = yt.title
    return title

def download_audio (link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription (link):
    audio_file = download_audio(link)
    aai.settings.api_key = "6cac73a5ea284b0c8002432861df7dd5"

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    os.remove(audio_file)

    return transcript.text

def generate_blog_from_transcription(transcription):
    openai.api_key = "sk-proj-8KpwFOxsv6LMlBrl5mdcT3BlbkFJQraRe2roUMwwagFLru7g"
    ## Can't generate blog because I am using free openai account and getting error 429: You exceeded your current quota
    
    #prompt = f"Based on the following transcript from a Youtube video, write a comprehensive blog article, write it based on the transcript, but do not make it looke like youtube video, make it proper blog article: \n\n {transcription} \n\nArticle:"

    #res = openai.completions.create(
    #   model = "gpt-3.5-turbo-instruct",
    #   prompt = prompt,
    #   max_tokens = 1000
    #)

    #generated_content = res.choices[0].text.strip()
    #return generated_content

    # Split the transcription into sentences
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', transcription)
    # Join the first 10 sentences
    return ' '.join(sentences[:20])

def blog_list(req):
    blog_articles = BlogPost.objects.filter(user = req.user)
    return render(req, "all-blogs.html", {'blog_articles': blog_articles})

def blog_details(req, pk):
    blog_article_details = BlogPost.objects.get(id = pk)
    if req.user == blog_article_details.user:
        return render(req, 'blog-details.html', {'blog_article_details': blog_article_details})

def user_login (req):
    if req.method == 'POST':
        username = req.POST['username']
        password = req.POST['password']

        user = authenticate(req, username=username, password=password)
        if user is not None:
            login(req, user)
            return redirect('/')
        else:
            error_message = 'Invalid username or password'
            return render(req, 'login.html', {'error_message': error_message})

    return render(req, 'login.html')

def user_signup (req):
    if req.method == 'POST':
        username = req.POST['username']
        email = req.POST['email']
        password = req.POST['password']
        repeatPassword = req.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(req, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(req, 'signup.html', {'error_message': error_message}) 
        else:
            error_message = 'Password do not match'
            return render(req, 'signup.html', {'error_message': error_message})

    return render(req, 'signup.html')

def user_logout (req):
    logout(req)
    return redirect('/')