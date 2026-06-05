import { Component, OnInit, OnDestroy, Input } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from 'src/environments/environment';

interface SensorData {
    temp: number;
    hum: number;
    co2: number;
    pm2p5: number;
    voc: number;
}

@Component({
    selector: 'app-sensors',
    templateUrl: './sensors.component.html',
    styleUrls: ['./sensors.component.css']
})

export class SensorsComponent implements OnInit, OnDestroy {
    @Input() allData: any;
    sensorsData: SensorData = {
        temp: 0,
        hum: 0,
        co2: 0,
        pm2p5: 0,
        voc: 0
    };
    private intervalId: any;
    private url = environment.api;

    constructor(private http: HttpClient) { }

    ngOnInit(): void {
        this.fetchData();
        this.intervalId = setInterval(() => {
            this.fetchData();
        }, 50000);
    }

    ngOnDestroy(): void {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }

    oaqData: any = null;

    fetchData() {
        this.http.get<SensorData>(`${this.url}/sensor/airquality`).subscribe({
            next: (data: SensorData) => {
                console.log('Sensors Data Received:', data);
                this.sensorsData = data;
            },
            error: (error: any) => {
                console.error('Error fetching sensor data:', error);
            }
        });
        
        this.http.get<any>(`${this.url}/oaq`).subscribe({
            next: (data: any) => {
                console.log('OAQ Data Received:', data);
                this.oaqData = data;
            },
            error: (error: any) => {
                console.error('Error fetching OAQ data:', error);
            }
        });
    }

    getTemp(temp: number | undefined): number {
        return temp ?? 0;
    }
    getHum(hum: number | undefined): number {
        return hum ?? 0;
    }
    getCO2(co2: number | undefined): number {
        return co2 ?? 0;
    }
    getPM2p5(pm2p5: number | undefined): number {
        return pm2p5 ?? 0;
    }
    getVOC(voc: number | undefined): number {
        return voc ?? 0;
    }
    getOAQPm2p5(): number {
        if (this.oaqData && this.oaqData.list && this.oaqData.list.length > 0) {
            return this.oaqData.list[0].components.pm2_5;
        }
        return 0;
    }
}
