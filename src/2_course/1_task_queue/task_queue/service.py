from .models import TaskQueue 
from django.db import transaction


@transaction.atomic
def fetch_task():
    task = (TaskQueue.objects
        .select_for_update(skip_locked=True)
        .filter(status='pending')
        .order_by('created_at')
        .first() 
    )

    if task is None:
        return None 
    
    task.status = 'in_progress'
    task.save()

    return task