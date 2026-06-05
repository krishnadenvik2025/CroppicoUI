import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private BASE_URL = environment.api;
  constructor (private http: HttpClient) { }

  // Post Api Call
  httpPost (method: string, body: any) {
    console.log("Http Post : ", method, body);
    return this.http.post<any>(this.BASE_URL + "/" + method, body);

  }
  // Get Api Call
  httpGet (endPoint: string) {
    console.log("Http Get : ", endPoint);
    return this.http.get<any>(this.BASE_URL + "/" + endPoint);

  }
}
