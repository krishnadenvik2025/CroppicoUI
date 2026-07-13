import { HttpClient } from '@angular/common/http';
import { Component, Input, Output, EventEmitter, OnChanges, OnInit, OnDestroy, SimpleChanges } from '@angular/core';
import { environment } from 'src/environments/environment';

interface SensorData {
    temp: number;
    hum: number;
    co2: number;
    pm2p5: number;
    voc: number;
    aqi: number;
}
// import { Apex } from './chartinfo';

@Component({
  selector: 'app-mainstatus',
  templateUrl: './mainstatus.component.html',
  styleUrls: ['./mainstatus.component.css']
})

export class MainstatusComponent implements OnInit, OnChanges, OnDestroy {
  @Input() meterData: any;
  @Input() allData: any;
  @Input() envData: any;
  @Output() screenChanged = new EventEmitter<number>();
  
  currentScreen: number = 0;
  totalScreens: number = 3;
  
  sensorsData: SensorData = { temp: 0, hum: 0, co2: 0, pm2p5: 0, voc: 0, aqi: 0 };
  private intervalId: any;

  constructor(private http: HttpClient) {
  }

  ngOnChanges(changes: SimpleChanges): void {
  }

  ngOnInit(): void {
    console.log("meterData",this.allData);
    this.fetchSensorData();
    this.intervalId = setInterval(() => {
        this.fetchSensorData();
    }, 50000);
    setTimeout(() => this.screenChanged.emit(this.currentScreen));
  }

  ngOnDestroy(): void {
    if (this.intervalId) {
        clearInterval(this.intervalId);
    }
  }

  fetchSensorData() {
    this.http.get<SensorData>(`${environment.api}/sensor/airquality`).subscribe({
        next: (data: SensorData) => {
            if(data) this.sensorsData = data;
        },
        error: (error: any) => {
            console.error('Error fetching sensor data:', error);
        }
    });
  }

  nextScreen() {
    if (this.currentScreen < this.totalScreens - 1) {
      this.currentScreen++;
      this.screenChanged.emit(this.currentScreen);
    }
  }

  prevScreen() {
    if (this.currentScreen > 0) {
      this.currentScreen--;
      this.screenChanged.emit(this.currentScreen);
    }
  }

  get aqiValue(): number {
    const aqi = this.sensorsData?.aqi || 0;
    return aqi
  }

  get aqiData() {
    const aqi = this.aqiValue;
    if (aqi <= 50) return { ring: '#00e400', txt: 'Good', bg: '#d4edda', fg: '#155724' }; 
    if (aqi <= 100) return { ring: '#ffff00', txt: 'Moderate', bg: '#fff9c4', fg: '#827717' }; 
    if (aqi <= 150) return { ring: '#ff7e00', txt: 'Unhealthy', bg: '#ffe0b2', fg: '#e65100' }; 
    if (aqi <= 200) return { ring: '#ff0000', txt: 'Unhealthy', bg: '#ffcdd2', fg: '#b71c1c' }; 
    if (aqi <= 300) return { ring: '#8f3f97', txt: 'Very Unhealthy', bg: '#e1bee7', fg: '#4a148c' }; 
    return { ring: '#7e0023', txt: 'Hazardous', bg: '#f8bbd0', fg: '#880e4f' }; 
  }
}
