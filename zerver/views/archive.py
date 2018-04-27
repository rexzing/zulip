from typing import List

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template import loader
from zerver.lib.streams import get_stream_by_id

from zerver.models import Message, UserProfile

from zerver.lib.avatar import get_gravatar_url
from zerver.lib.timestamp import datetime_to_timestamp

def archive(request: HttpRequest,
            stream_id: int,
            topic_name: str) -> HttpResponse:
    stream = get_stream_by_id(stream_id)

    def get_response(rendered_message_list: List[str], is_web_public: bool) -> HttpResponse:
        return render(
            request,
            'zerver/archive/index.html',
            context={
                'is_web_public': is_web_public,
                'message_list': rendered_message_list,
                'stream': stream.name,
                'topic': topic_name,
            }
        )

    if not stream.is_web_public:
        return get_response([], False)

    all_messages = list(Message.objects.select_related(
        'sender').filter(recipient__type_id=stream_id, subject=topic_name).order_by('pub_date'))
    if not all_messages:
        return get_response([], True)

    rendered_message_list = []
    prev_sender = None
    for msg in all_messages:
        include_sender = False
        status_message = Message.is_status_message(msg.content, msg.rendered_content)
        if not prev_sender or prev_sender != msg.sender or status_message:
            if status_message:
                prev_sender = None
            else:
                prev_sender = msg.sender
            include_sender = True
        if status_message:
            status_message = msg.rendered_content[4+3: -4]
        context = {
            'sender_full_name': msg.sender.full_name,
            'timestampstr': datetime_to_timestamp(msg.last_edit_time
                                                  if msg.last_edit_time
                                                  else msg.pub_date),
            'message_content': msg.rendered_content,
            'avatar_url': get_gravatar_url(msg.sender.email, 1),
            'include_sender': include_sender,
            'status_message': status_message,
        }
        rendered_msg = loader.render_to_string('zerver/archive/single_message.html', context)
        rendered_message_list.append(rendered_msg)
    return get_response(rendered_message_list, True)