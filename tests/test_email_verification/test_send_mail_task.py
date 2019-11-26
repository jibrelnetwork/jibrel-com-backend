from jibrel.notifications.tasks import send_mail


def test_send_mail_task(mailoutbox):
    kwargs = dict(
        subject='subject',
        txt_content='txt_content',
        html_content='<p>html_content</p>',
        recipient='email@email.com',
        from_email='another@email.com',
        task_context={}
    )
    send_mail(**kwargs)
    assert len(mailoutbox) == 1
    mail = mailoutbox[0]
    assert mail.subject == kwargs['subject']
    assert mail.body == kwargs['txt_content']
    assert len(mail.alternatives) > 0
    assert (kwargs['html_content'], 'text/html') in mail.alternatives
