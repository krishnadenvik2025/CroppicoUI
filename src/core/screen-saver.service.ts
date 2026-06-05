import { Injectable } from '@angular/core';
import { BehaviorSubject, observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ScreenSaverService {

  constructor() { }

  public screenSaverBehaviorSubject=new BehaviorSubject(true);
  public screenSaver = this.screenSaverBehaviorSubject.asObservable();

  public updateScreenSaverStatus(status:boolean )
  {
    this.screenSaverBehaviorSubject.next(status)
  }
}
